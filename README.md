# Learning to Solve Bilevel Programs with Binary Tender
This repository contains the source code used in the computational experiments of the paper: **Learning to Solve Bilevel Programs with Binary Tender** (available on OpenReview.net [https://openreview.net/pdf?id=PsDFgTosqb]).

In this paper, we develop deep learning techniques to address this challenge. Specifically, we consider a BP with binary tender, wherein the upper and lower levels are linked via binary variables. We train a neural network to approximate the optimal value of the lower-level problem, as a function of the binary tender. Then, we obtain a single-level reformulation of the BP through a mixed-integer representation of the value function. Furthermore, we conduct a comparative analysis between two types of neural networks: general neural networks and the novel input supermodular neural networks, studying their representational capacities. To solve high-dimensional BPs, we introduce an enhanced sampling method to generate higher-quality samples and implement an iterative process to refine solutions.

## Prerequisites
Before you use the code, ensure you have met the following requirements:

* You have access of Gurobi. It is used as the optimization solver for various linear programming and integer programming models in the code.
* You have a basic understanding of column generation approach.

## Test Instances
There are three classes of test instances included in the computational experiments:

* Modified VRPTW Instances
* CVRP X-Instances
* Medical Home Delivery in Wayne County Intances (multi-depot) 

They are provided in the folder `/Instances`

## How to Use
One can create a project and use the code in this repository in Java IDE by selecting "create new project with existing sources". However, the user need to have Gurobi solver installed and add it as global library to this project.

The driver of the computation is `src/RandCol/NumericalTests`. However, it only serves as an example of how to call the solver. The code may need to be modified based on the operating systems.

The original source code of pulse algorithm is under `src/Pulse` and the code for our random coloring algorithm is under `src/RandCol`.
