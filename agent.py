# -*- coding: utf-8 -*-
"""ygundepa_agent.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Pl_vJkxQyXOt_FTAOSelKLtdyi6EL-5T
"""

class Agent():
    def __init__(self, action_size):
        self.action_size = action_size

        # These are hyper parameters for the DQN
        self.discount_factor = 0.99
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.explore_step = 500000
        self.epsilon_decay = (self.epsilon - self.epsilon_min) / self.explore_step
        self.train_start = 100000
        self.update_target = 1000

        # Generate the memory
        self.memory = ReplayMemory()

        # Create the policy net and the target net
        self.policy_net = DQN(action_size)
        self.policy_net.to(device)
        self.target_net = DQN(action_size)
        self.target_net.to(device)
        
        self.optimizer = optim.Adam(params=self.policy_net.parameters(), lr=learning_rate)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=scheduler_step_size, gamma=scheduler_gamma)

        # Initialize a target network and initialize the target network to the policy net
        self.update_target_net()

    def load_policy_net(self, path):
        self.policy_net = torch.load(path)           

    # after some time interval update the target net to be same with policy net
    def update_target_net(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())

    """Get action using policy net using epsilon-greedy policy"""
    def get_action(self, state):
        if np.random.rand() <= self.epsilon:
            temp = []
            random_number = random.randrange(self.action_size)
            temp.append([random_number])
            return torch.tensor(temp, device=device, dtype=torch.long)
        else:
            with torch.no_grad():
                state_tensor = torch.tensor([state], device=device)
                q_values = self.policy_net(state_tensor)
                action = q_values.argmax().item()
            return torch.tensor([[action]], device=device, dtype=torch.long)


    def train_policy_net(self, frame):
        if self.epsilon > self.epsilon_min:
            self.epsilon -= self.epsilon_decay

        mini_batch = self.memory.sample_mini_batch(frame)
        mini_batch = np.array(mini_batch).transpose()

        history = np.stack(mini_batch[0], axis=0)
        states = np.float32(history[:, :4, :, :]) / 255.
        states = torch.from_numpy(states).cuda()
        actions = list(mini_batch[1])
        actions = torch.LongTensor(actions).cuda()
        rewards = list(mini_batch[2])
        rewards = torch.FloatTensor(rewards).cuda()
        next_states = np.float32(history[:, 1:, :, :]) / 255.
        next_states = torch.tensor(next_states).cuda()

        dones = mini_batch[3] # checks if the game is over
        musk = torch.tensor(list(map(int, dones==False)),dtype=torch.bool)
        
        # Compute Q(s_t, a), the Q-value of the current state
        state_action_values = self.policy_net(states)[range(batch_size), actions.view(batch_size).long()]

        # Compute Q function of next state
        next_state_values = torch.zeros(batch_size, device=device)
        temp = [s is not None for s in next_states]
        non_final_mask = torch.tensor(temp, device=device, dtype=torch.bool)
        temp2 = [s for s in next_states if s is not None]
        non_final_ns = torch.stack(temp2).to(device)

        # Find maximum Q-value of action at next state from policy net
        next_state_values[non_final_mask] = self.target_net(non_final_ns).max(1)[0].detach()


        next_mul_discount = next_state_values * self.discount_factor
        expected_value =  next_mul_discount + rewards
        reshaped_state_action_value = state_action_values.view(32)

        # Compute the Huber Loss
        loss = F.smooth_l1_loss(reshaped_state_action_value, expected_value)

        self.optimizer.zero_grad()
        loss.backward()

        # Optimize the model, .step() both the optimizer and the scheduler!
        for param in self.policy_net.parameters():
            param.grad.data.clamp_(-1, 1)

        self.optimizer.step()