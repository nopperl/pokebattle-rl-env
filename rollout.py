from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import ray
from ray.rllib.optimizers import SampleBatch


def collect_samples(agents, config, local_evaluator):
    num_timesteps_so_far = 0
    trajectories = []
    # This variable maps the object IDs of trajectories that are currently
    # computed to the agent that they are computed on; we start some initial
    # tasks here.

    agent_dict = {}

    for agent in agents:
        fut_sample = agent.sample.remote()
        agent_dict[fut_sample] = agent

    while num_timesteps_so_far < config["timesteps_per_batch"]:
        # TODO(pcm): Make wait support arbitrary iterators and remove the
        # conversion to list here.
        ids, _ = ray.wait(list(agent_dict), num_returns=len(agent_dict))
        new_ids = []
        for id in ids:
            agent = agent_dict.pop(id)
            # Start task with next trajectory and record it in the dictionary.
            fut_sample = agent.sample.remote()
            agent_dict[fut_sample] = agent
            new_ids.append(fut_sample)
        for id in new_ids:
            next_sample = ray.get(id)
            num_timesteps_so_far += next_sample.count
            trajectories.append(next_sample)
    return SampleBatch.concat_samples(trajectories)
