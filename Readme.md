Pokémon battle RL environment
===

This repository contains a Reinforcement Learning environment for Pokémon battles.

In particular, the environment consists of three parts:
* A [Gym Env](https://github.com/openai/gym) which serves as interface between RL agents and battle simulators
* A BattleSimulator base class, which handles typical Pokémon game state
* Simulator classes derived from BattleSimulator, which access and interact with different simulators to extract data

Currently, only a [Pokemon Showdown](https://github.com/Zarel/Pokemon-Showdown) integration is planned, but in theory this structure allows for integrations with different simulators (eg Console emulators).
