.. Pokemon battle RL environment documentation master file, created by
   sphinx-quickstart on Thu Mar  1 18:38:19 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Pokemon battle RL environment documentation
===========================================

This repository contains a Reinforcement Learning environment for Pokémon battles.

In particular, the environment consists of three parts:

* A `Gym Env <https://github.com/openai/gym>`_ which serves as interface between RL agents and battle simulators
* A BattleSimulator base class, which handles typical Pokémon game state
* Simulator classes derived from BattleSimulator, which access and interact with different simulators to extract data

Currently, only a `Pokemon Showdown <https://github.com/Zarel/Pokemon-Showdown>`_ integration is planned, but in theory this structure allows for integrations with different simulators (eg Console emulators).


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules

.. automodule:: pokebattle_rl_env.battle_simulator
   :members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`





