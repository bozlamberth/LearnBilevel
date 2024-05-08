# Learning to Solve Bilevel Programs with Binary Tender
This repository contains the source code used in the computational experiments of the paper: Learning to Solve Bilevel Programs with Binary Tender (available on OpenReview.net [https://openreview.net/pdf?id=PsDFgTosqb]).

In our paper, we solve Vehicle Routing Problem with Unit Demand using column generation approach. We promote a random coloring algorithm that solves the elmentary shortest path problem with resource constraints (ESPPRC), which serves as the subproblem of column generation-based approach for Vehicle Routing Problem.

Prerequisites
Before you use the code, ensure you have met the following requirements:

You have access of Gurobi. It is used as the optimization solver for various linear programming and integer programming models in the code.
You have a basic understanding of column generation approach.
Test Instances
There are three classes of test instances included in the computational experiments:

Modified VRPTW Instances
CVRP X-Instances
Medical Home Delivery in Wayne County Intances (multi-depot)
They are provided in the folder /Instances

How to Use
One can create a project and use the code in this repository in Java IDE by selecting "create new project with existing sources". However, the user need to have Gurobi solver installed and add it as global library to this project.

The driver of the computation is src/RandCol/NumericalTests. However, it only serves as an example of how to call the solver. The code may need to be modified based on the operating systems.

The original source code of pulse algorithm is under src/Pulse and the code for our random coloring algorithm is under src/RandCol.
