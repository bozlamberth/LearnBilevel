import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pyomo.environ as pe
import pao.pyomo as pao
import cvxpy as cp
import time
from NNmodel import *
from scipy.linalg import orth


class InstanceLP(object):
    def __init__(self, num_x, num_y, num_cstsUL, num_cstsLL):
        """
        min  c*x+d1*y
        s.t.    A1*x<=b1 # + B1*y
                x in {0, 1}
                y = arg max d2*y
                            s.t.    A2*x+B2*y<=b2
                                    ymin<=y<=ymax
        """
        # parameter setting
        self.num_x = num_x
        self.num_y = num_y
        self.num_cstsUL = num_cstsUL
        self.num_cstsLL = num_cstsLL

        self.cmax = 100
        self.dmax = 100
        self.ABmax = 10 * 20 / (self.num_x + self.num_y)
        self.b1min = 10
        self.b1max = 110
        self.b2min = 30
        self.b2max = 130
        self.ymax=1
        self.ymin=0

        # self.c, self.d1, self.d2, self.A1, self.B1, self.b1, self.A2, self.B2, self.b2, self.bp = self.InstanceGen()
        # self.c, self.d1, self.d2, self.A1, self.B1, self.b1, self.A2, self.B2, self.b2, self.bp = self.InstanceRead('InstanceLP.xlsx')
        self.c, self.d1, self.d2, self.A1, self.B1, self.b1, self.A2, self.B2, self.b2, self.bp = self.InstanceRead('InstanceLP_x'+str(num_x)+'y20.xlsx')

        self.time_total = 0
        self.time_sampling = 0
        self.time_training = 0
        self.time_solving = 0
        self.value_x = None
        self.value_y = None
        self.value_objctv = None
        self.UB = float('inf')
        self.LB = -float('inf')
        self.flag = 'unsolved'
        self.num_iter_enhanced = 3
        self.solutionHistory = []

    def InstanceGen(self):
        for iter in range(100):
            # parameter generation
            c = (np.random.rand(1, self.num_x) - 0.5) * self.cmax
            d1 = (np.random.rand(1, self.num_y) - 0.5) * self.dmax
            d2 = d1  # (np.random.rand(1, self.num_y) - 0.5) * self.dmax
            A1 = 2 * (np.random.rand(self.num_cstsUL, self.num_x) - 0.5) * self.ABmax * 2
            B1 = 2 * (np.random.rand(self.num_cstsUL, self.num_y) - 0.5) * self.ABmax * 1
            b1 = np.random.rand(self.num_cstsUL, 1) * (self.b1max - self.b1min) + self.b1min
            A2 = 2 * (np.random.rand(self.num_cstsLL, self.num_x) - 0.5) * self.ABmax * 10
            B2 = 2 * (np.random.rand(self.num_cstsLL, self.num_y) - 0.5) * self.ABmax * 1
            b2 = np.random.rand(self.num_cstsLL, 1) * (self.b2max - self.b2min) + self.b2min

            # solve problem, FA, REG, PCCG, MIBS
            bp = self.InstanceBuild(c, d1, d2, A1, B1, b1, A2, B2, b2)
            with pao.Solver('pao.pyomo.MIBS') as solver:
                results = solver.solve(bp, tee=True)  # 'threads': 4, options={'mipgap': 100}
            if results.solver.best_feasible_objective == None:
                continue
            value_x = []
            for i in bp.x:
                value_x.append(pe.value(bp.x[i]))
            value_x = np.array(value_x)
            value_y = []
            for i in bp.y:
                value_y.append(pe.value(bp.y[i]))
            value_y = np.array(value_y)
            value_objctv = np.array([pe.value(bp.objctv)])
            print('\nOptimal solution:')
            print('min cost =', np.round(value_objctv, 2))
            print('x =', np.int_(value_x))
            print('y =', np.round(value_y, 2))
            break

        # save instance
        FileName = 'InstanceLP.xlsx'
        writer = pd.ExcelWriter(FileName)
        wrt = pd.DataFrame(c)
        wrt.to_excel(writer, 'c', header=None, index=False)
        wrt = pd.DataFrame(d1)
        wrt.to_excel(writer, 'd1', header=None, index=False)
        wrt = pd.DataFrame(d2)
        wrt.to_excel(writer, 'd2', header=None, index=False)
        wrt = pd.DataFrame(A1)
        wrt.to_excel(writer, 'A1', header=None, index=False)
        wrt = pd.DataFrame(B1)
        wrt.to_excel(writer, 'B1', header=None, index=False)
        wrt = pd.DataFrame(b1)
        wrt.to_excel(writer, 'h1', header=None, index=False)
        wrt = pd.DataFrame(A2)
        wrt.to_excel(writer, 'A2', header=None, index=False)
        wrt = pd.DataFrame(B2)
        wrt.to_excel(writer, 'B2', header=None, index=False)
        wrt = pd.DataFrame(b2)
        wrt.to_excel(writer, 'h2', header=None, index=False)
        wrt = pd.DataFrame([self.ymax, self.ymin])
        wrt.to_excel(writer, 'y', header=None, index=False)
        # wrt = pd.DataFrame([value_x, value_y, value_objctv])
        # wrt.to_excel(writer, 'solution', header=None, index=False)
        writer.close()
        print('successfully export instance as', FileName)

        return c, d1, d2, A1, B1, b1, A2, B2, b2, bp

    def InstanceRead(self, FileName):
        instance = pd.read_excel(io=FileName, sheet_name=None, header=None)
        c = instance['c'].values
        d1 = instance['d1'].values
        d2 = instance['d2'].values
        A1 = instance['A1'].values
        B1 = instance['B1'].values
        b1 = instance['h1'].values
        A2 = instance['A2'].values
        B2 = instance['B2'].values
        b2 = instance['h2'].values
        temp = instance['y'].values
        self.ymax = temp[0, 0]
        self.ymin = temp[1, 0]
        self.num_x = len(A2[0, :])
        self.num_y = len(B2[0, :])
        self.num_cstsUL = len(A1[:, 0])
        self.num_cstsLL = len(A2[:, 0])
        bp = self.InstanceBuild(c, d1, d2, A1, B1, b1, A2, B2, b2)
        return c, d1, d2, A1, B1, b1, A2, B2, b2, bp

    def InstanceBuild(self, c, d1, d2, A1, B1, b1, A2, B2, b2):
        bp = pe.ConcreteModel()
        bp.x = pe.Var(range(self.num_x), within=pe.Binary)
        bp.y = pe.Var(range(self.num_y), bounds=(self.ymin, self.ymax))
        # Upper level
        bp.objctv = pe.Objective(expr=c[0, :] @ bp.x + d1[0, :] @ bp.y, sense=pe.minimize)
        bp.cstsUL = pe.ConstraintList()
        for i in range(self.num_cstsUL):
            bp.cstsUL.add(expr=A1[i, :] @ bp.x <= b1[i, 0])  #  + B1[i, :] @ bp.y
        # Lower level - declaration
        bp.LL = pao.SubModel(fixed=bp.x)
        bp.LL.objctv = pe.Objective(expr=d2[0, :] @ bp.y, sense=pe.maximize)
        bp.LL.cstsLL = pe.ConstraintList()
        for i in range(self.num_cstsLL):
            bp.LL.cstsLL.add(expr=A2[i, :] @ bp.x + B2[i, :] @ bp.y <= b2[i, 0])
        return bp

    def solve(self, solverName):
        if solverName == 'HPR':
            self.solveByHPR()
        elif solverName in ['FA', 'REG', 'PCCG', 'MIBS']:
            self.solveBySolver(solverName)
        elif solverName in ['GNN', 'ISNN']:
            # self.solveByNN(solverName)
            self.solveByNNEnhanced(solverName)
        return

    def solveByHPR(self):
        # model
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y)
        objctv = self.c @ x + self.d1 @ y
        csts = [
            self.ymin <= y, y <= self.ymax,
            self.A1 @ x <= self.b1[:, 0],  # + self.B1 @ y
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0]
        ]

        # solve
        prbl = cp.Problem(cp.Minimize(objctv), csts)
        T1 = time.time()
        prbl.solve(solver=cp.GUROBI, verbose=False)  # , threads=4

        # save results
        if prbl.status != 'optimal':
            self.flag = 'infeasible'
            self.solutionPrint()
        else:
            self.flag = 'solved optimal'
            self.value_x = x.value
            self.value_y = y.value
            self.value_objctv = objctv.value[0]
            self.LB = max(self.LB, self.value_objctv)
            self.solutionCheck()
            T2 = time.time()
            self.time_total = T2 - T1
            self.time_solving = T2 - T1
            self.solutionPrint()
        return

    def solveBySolver(self, solverName):
        # solve
        T1 = time.time()
        with pao.Solver('pao.pyomo.' + solverName) as solver:
            results = solver.solve(self.bp, tee=True)  # , options={'threads': 4}

        # save results
        if results.solver.best_feasible_objective == None:
            self.flag = 'infeasible'
            self.solutionPrint()
        else:
            self.flag = 'solved optimal'
            value_x = []
            for i in self.bp.x:
                value_x.append(pe.value(self.bp.x[i]))
            value_x = np.array(value_x)
            value_y = []
            for i in self.bp.y:
                value_y.append(pe.value(self.bp.y[i]))
            value_y = np.array(value_y)
            value_objctv = pe.value(self.bp.objctv)
            self.value_x = value_x
            self.value_y = value_y
            self.value_objctv = value_objctv
            self.solutionCheck()
            T2 = time.time()
            self.time_total = T2-T1
            self.time_solving = T2-T1
            self.LB = max(self.LB, self.value_objctv)
            self.solutionPrint()
        return

    def solveByNN(self, solverName, num_samples=1000):
        # parameter
        flag_ISNN = True if solverName == 'ISNN' else False
        flag_doubleX = flag_ISNN & True
        self.solveByHPR()
        value_x = self.value_x
        value_y = self.value_y
        value_objctv = self.value_objctv

        # sampling
        T1 = time.time()
        num_samples = min(num_samples, 2 ** self.num_x)
        samples = self.samplesGen(num_samples)
        # samples = self.samplesRead('SamplesLP.xlsx')
        num_samples_obtained = len(samples[:, 0])
        T3 = time.time()

        # training
        num_layer = 2
        num_input = self.num_x * (2 if flag_doubleX == True else 1)
        num_hidden = calculateNumHidden(num_samples_obtained, num_layer, num_input, flag_ISNN)
        num_output = 1
        NNArchitecture = [num_input, num_hidden, num_hidden, num_output]
        NN = NNmodel(NNArchitecture, flag_ISNN, flag_doubleX)
        NN.train(samples[:, 0:-1])
        # NN.readParameters('NNparametersISNN.xlsx' if NN.flag_ISNN else 'NNparametersGNN.xlsx')
        T4 = time.time()

        # solving
        self.solveByGNN(NN)
        self.solutionCheck()
        self.solutionPrint()
        if self.value_objctv > value_objctv:
            self.value_x = value_x
            self.value_y = value_y
            self.value_objctv = value_objctv
        else:
            value_x = self.value_x
            value_y = self.value_y
            value_objctv = self.value_objctv
        if self.value_objctv > min(samples[:,-1]):
            idx = np.argmin(samples[:, -1])
            self.value_x = samples[idx, 0:self.num_x]
            self.value_objctv = samples[idx, self.num_x+1]
            self.solutionCheck()
            self.flag = 'optimal in samples'
        T2 = time.time()
        self.time_total = T2 - T1
        self.time_sampling = T3 - T1
        self.time_training = T4 - T3
        self.time_solving = T2 - T4
        self.solutionPrint()

        return

    def solveByNNEnhanced(self, solverName, num_samples=1000):
        # parameter
        flag_ISNN = True if solverName == 'ISNN' else False
        flag_doubleX = flag_ISNN & True

        self.solveByHPR()
        value_x = self.value_x
        value_y = self.value_y
        value_objctv = self.value_objctv
        NN = None
        num_sampling = num_samples * 10
        max_repeated = 1000
        samples_all = np.zeros((0, self.num_x+2))
        for Ind_iter in range(self.num_iter_enhanced):
            # sampling
            T1 = time.time()
            samples = self.samplesGenEnhanced(num_samples, self.UB, NN, num_sampling, max_repeated)
            # samples = self.samplesRead('SamplesLP.xlsx')
            if len(samples) == 0:
                self.flag = 'insufficient samples'
                self.solutionSave(Ind_iter)
                break
            samples_all = np.vstack([samples_all, samples])
            samples_all = np.unique(samples_all, axis=0)
            num_samples_all = len(samples_all[:, 0])
            self.samplesSave(samples_all)
            T3 = time.time()
            self.time_sampling += T3-T1

            # training
            num_layer = 2
            num_input = self.num_x * (2 if flag_doubleX == True else 1)
            num_hidden = calculateNumHidden(num_samples_all, num_layer, num_input, flag_ISNN)
            num_output = 1
            NNArchitecture = [num_input, num_hidden, num_hidden, num_output]
            NN = NNmodel(NNArchitecture, flag_ISNN, flag_doubleX)
            NN.train(samples_all[:, 0:-1])  # -num_samples
            # NN.readParameters('NNparametersISNN.xlsx' if NN.flag_ISNN else 'NNparametersGNN.xlsx')
            T4 = time.time()
            self.time_training += T4-T3

            # solving
            self.solveByGNN(NN)
            self.solutionCheck()
            self.solutionPrint()
            if self.value_objctv > value_objctv:
                self.value_x = value_x
                self.value_y = value_y
                self.value_objctv = value_objctv
            else:
                value_x = self.value_x
                value_y = self.value_y
                value_objctv = self.value_objctv
            if self.value_objctv > min(samples_all[:,-1]):
                idx = np.argmin(samples_all[:, -1])
                self.value_x = samples_all[idx, 0:self.num_x]
                self.value_objctv = samples_all[idx, self.num_x+1]
                self.solutionCheck()
                self.flag = 'optimal in samples'
            T2 = time.time()
            self.time_solving += T2-T4
            self.time_total = self.time_sampling + self.time_training + self.time_solving
            self.solutionPrint()
            self.solutionSave(Ind_iter)

        return

    def solveByGNN(self, NN):
        # parameters
        bigM = 10

        # model
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y)
        phi = cp.Variable()
        z = []
        z_temp = []
        z_sign = []
        for i in range(NN.num_layer_hidden + 2):
            z += [cp.Variable(NN.Architecture[i])]
            z_temp += [cp.Variable(NN.Architecture[i])]
            z_sign += [cp.Variable(NN.Architecture[i], boolean=True)]
        objctv = self.c @ x + self.d1 @ y
        csts = [
            self.ymin <= y, y <= self.ymax,
            self.A1 @ x <= self.b1[:, 0],  # + self.B1 @ y
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0],
            self.d2 @ y >= phi,
            z[-1] * (NN.label_max - NN.label_min) + NN.label_min == phi
        ]
        if NN.flag_doubleX:
            csts += [z[0] == cp.hstack([x, 1 - x])]
        else:
            csts += [z[0] == x]
        for i in range(NN.num_layer_hidden + 1):
            if i == 0:
                csts += [
                    z_temp[i+1] == NN.w[i] @ z[i] + NN.b[i][:, 0],
                    0 <= z[i+1], z[i+1] <= bigM * z_sign[i+1],
                    z_temp[i+1] <= z[i+1], z[i+1] <= z_temp[i+1] + bigM * (1 - z_sign[i+1])
                ]
            else:
                csts += [
                    z_temp[i+1] == NN.w[i] @ cp.hstack([z[i], z[0]]) + NN.b[i][:, 0],
                    0 <= z[i+1], z[i+1] <= bigM * z_sign[i+1],
                    z_temp[i+1] <= z[i+1], z[i+1] <= z_temp[i+1] + bigM * (1 - z_sign[i+1])
                ]

        # solve
        prbl = cp.Problem(cp.Minimize(objctv), csts)
        prbl.solve(solver=cp.GUROBI, verbose=True)  # , threads=4

        # save results
        if prbl.status != 'optimal':
            self.flag = 'infeasible'
        else:
            self.flag = 'solved optimal'
            self.value_x = x.value
            self.value_y = y.value
            self.value_objctv = objctv.value[0]
        return

    def solveByISNN(self, NN):
        def funcPhi(S):
            temp = np.zeros(self.num_x * (2 if NN.flag_doubleX == True else 1))
            for i in S:
                temp[i] = 1
            return NN.predict(temp)

        def funcRho(S, k):
            Sk = S.copy()
            Sk.add(k)
            return funcPhi(Sk) - funcPhi(S)

        def funcNk(num_x_temp, k):
            temp = set(range(num_x_temp))
            temp.remove(k)
            return temp

        # model
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y)
        x_temp = cp.Variable(self.num_x * (2 if NN.flag_doubleX == True else 1), boolean=True)
        objctv = self.c @ x + self.d1 @ y
        csts = [
            self.ymin <= y, y <= self.ymax,
            self.A1 @ x <= self.b1[:, 0],  # + self.B1 @ y
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0]
        ]
        if NN.flag_doubleX:
            csts += [x_temp == cp.hstack([x, 1 - x])]
        else:
            csts += [x_temp == x]

        # solve
        value_phi = 1e6
        value_objctvLL = 0
        count = 0
        while value_objctvLL < value_phi:
            # solution
            prbl = cp.Problem(cp.Minimize(objctv), csts)
            prbl.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
            count += 1
            print(count)
            # update value
            value_x_temp = x_temp.value
            value_y = y.value
            value_objctvLL = self.d2 @ value_y
            value_objctvLL = value_objctvLL[0]
            value_phi = NN.predict(value_x_temp)
            if value_objctvLL + 1e-6 >= value_phi:
                break
            # add supermodularity inequality
            S = np.where(np.int_(value_x_temp) == 1)
            S = set(S[0])
            nS = np.where(np.int_(value_x_temp) == 0)
            nS = set(nS[0])
            csts += [
                self.d2 @ y >= funcPhi(S) - sum(funcRho(funcNk(self.num_x*(2 if NN.flag_doubleX == True else 1), k), k) * (1 - x_temp[k]) for k in S)
                                         + sum(funcRho(S, k) * x_temp[k] for k in nS)
            ]

        # save results
        self.flag = 'solved optimal'
        self.value_x = x.value
        self.value_y = y.value
        self.value_objctv = objctv.value[0]
        return

    def samplesRead(self, FileName):
        data = pd.read_excel(io=FileName, sheet_name=None, header=None)
        samples = data['samples'].values
        return samples

    def samplesGen(self, num_samples, num_sampling=10000, max_repeated=1000):
        def BE(num_x, i):
            strx = '{:0' + str(num_x) + 'b}'
            ii = strx.format(i)
            sample = []
            for iii in range(num_x):
                sample.append(int(ii[iii]))
            return sample

        # lower-level problem
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y)
        objctv = self.d2 @ y
        csts = [
            self.ymin <= y, y <= self.ymax,
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0]
        ]
        # sampling
        samples = []
        UBlist = []
        if 2**self.num_x <= num_samples:
            for i in range(2**self.num_x):
                sample = BE(self.num_x, i)
                prbl = cp.Problem(cp.Maximize(objctv), csts+[x == sample])
                prbl.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
                phi = objctv.value[0] if prbl.status == 'optimal' else None
                if phi == None:
                    print(i+1, '/', 2**self.num_x, ': Infeasible')
                    continue
                UB = self.c @ sample + self.d1 @ y.value
                UBlist.append(UB)
                samples.append(list(sample)+[phi]+list(UB))
                print(i+1, '/', 2**self.num_x, ', Optimal (count_samples=', len(samples), 'UB=', UB, ')')
        else:
            record = []
            max_iter = num_sampling
            count_repeated = 0
            for i in range(max_iter):
                if (len(record) >= 2**self.num_x) | (count_repeated > max_repeated):
                    break
                temp = int(np.round(np.random.rand() * (2**self.num_x-1)))
                if temp in record:
                    count_repeated += 1
                    print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', repeated')
                    continue
                else:
                    count_repeated = 0
                    record.append(temp)
                sample = BE(self.num_x, temp)
                prbl = cp.Problem(cp.Maximize(objctv), csts+[x == sample])
                prbl.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
                phi = objctv.value[0] if prbl.status == 'optimal' else None
                if phi == None:
                    print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', Infeasible')
                    continue
                UB = self.c @ sample + self.d1 @ y.value
                UBlist.append(UB)
                samples.append(list(sample)+[phi]+list(UB))
                print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', Optimal (count_samples=', len(samples), 'UB=', UB, ')')
                if len(samples) >= num_samples:
                    break
        # export samples
        print(min(UBlist))
        self.samplesSave(samples)
        self.samplesPrint(samples)
        return np.array(samples)

    def samplesGenEnhanced(self, num_samples, UB, NN=None, num_sampling=10000, max_repeated=1000):
        # parameters
        bigM = 10
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y)

        # sampling problem
        csts0 = [
            self.ymin <= y, y <= self.ymax,
            self.A1 @ x <= self.b1[:, 0],  # + self.B1 @ y
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0],
            self.c @ x + self.d1 @ y <= UB,
        ]
        # if NN == None:
        #     if UB != float('inf'):
        #         csts0 += [
        #             self.c @ x + self.d1 @ y <= UB,
        #         ]
        # else:
        #     phi = cp.Variable()
        #     z = []
        #     z_temp = []
        #     z_sign = []
        #     for i in range(NN.num_layer_hidden + 2):
        #         z += [cp.Variable(NN.Architecture[i])]
        #         z_temp += [cp.Variable(NN.Architecture[i])]
        #         z_sign += [cp.Variable(NN.Architecture[i], boolean=True)]
        #     csts0 += [
        #         self.c @ x + self.d1 @ y + 1 * (phi - self.d2 @ y) <= UB,
        #         z[-1] * (NN.label_max - NN.label_min) + NN.label_min == phi
        #     ]
        #     if NN.flag_doubleX:
        #         csts0 += [z[0] == cp.hstack([x, 1 - x])]
        #     else:
        #         csts0 += [z[0] == x]
        #     for i in range(NN.num_layer_hidden + 1):
        #         if i == 0:
        #             csts0 += [
        #                 z_temp[i+1] == NN.w[i] @ z[i] + NN.b[i][:, 0],
        #                 0 <= z[i+1], z[i+1] <= bigM * z_sign[i+1],
        #                 z_temp[i+1] <= z[i+1], z[i+1] <= z_temp[i+1] + bigM * (1 - z_sign[i+1])
        #             ]
        #         else:
        #             csts0 += [
        #                 z_temp[i+1] == NN.w[i] @ cp.hstack([z[i], z[0]]) + NN.b[i][:, 0],
        #                 0 <= z[i+1], z[i+1] <= bigM * z_sign[i+1],
        #                 z_temp[i+1] <= z[i+1], z[i+1] <= z_temp[i+1] + bigM * (1 - z_sign[i+1])
        #             ]

        # lower-level problem
        objctv = self.d2 @ y
        csts = [
            self.ymin <= y, y <= self.ymax,
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0]
        ]

        # sampling
        samples = []
        record = []
        UBlist = []
        max_iter = num_sampling
        count_repeated = 0
        count_infeasible = 0
        for i in range(max_iter):
            if (len(record) >= 2**self.num_x) | (count_repeated > max_repeated) | (count_infeasible > max_repeated/2):
                break
            h = 2 * np.random.rand(1, self.num_x) - 1
            D = np.diag(np.random.rand(self.num_x))
            U = orth(np.random.rand(self.num_x, self.num_x))
            Q = U.T @ D @ U
            objctv0 = h @ x + x.T @ cp.psd_wrap(Q) @ x
            prbl0 = cp.Problem(cp.Minimize(objctv0), csts0)
            prbl0.solve(solver=cp.GUROBI, verbose=False)  # , threads=4, MIPFocus=1, MIPGap=20
            if prbl0.status != 'optimal':
                print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', ' Infeasible')
                count_infeasible += 1
                continue
            sample = np.int_(x.value)
            temp = 2**np.array(range(self.num_x)) @ sample
            if temp in record:
                count_repeated += 1
                print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', repeated')
                continue
            else:
                count_repeated = 0
                record.append(temp)
            prbl = cp.Problem(cp.Maximize(objctv), csts+[x == sample])
            prbl.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
            phi = objctv.value[0] if prbl.status == 'optimal' else None
            if phi == None:
                print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', Infeasible')
                continue
            UB = self.c @ sample + self.d1 @ y.value
            UBlist.append(UB)
            samples.append(list(sample)+[phi]+list(UB))
            print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', Optimal (count_samples=', len(samples), 'UB=', UB, ')')
            count_infeasible = 0
            if len(samples) >= num_samples:
                break
        # export samples
        if len(UBlist)==0:
            return np.zeros((0, self.num_x+2))
        print(min(UBlist))
        self.samplesSave(samples)
        self.samplesPrint(samples)
        return np.array(samples)

    def samplesPrint(self, samples):
        zz = []
        for i in range(len(samples)):
            if samples[i][self.num_x] not in zz:
                zz.append(samples[i][self.num_x])
        zz.sort()
        print(zz[0], '-', zz[-1])
        plt.figure()
        plt.plot(zz)
        plt.title('sample_value')
        plt.show()

    def samplesSave(self, samples):
        FileName = 'SamplesLP.xlsx'
        writer = pd.ExcelWriter(FileName)
        wrt = pd.DataFrame(samples)
        wrt.to_excel(writer, 'samples', header=None, index=False)
        writer.close()
        print('successfully export samples as ', FileName)

    def solutionCheck(self):
        print('cost =', round(self.value_objctv, 2))
        # check feasibility
        temp1 = np.max(self.A1 @ self.value_x - self.b1[:, 0])  # + self.B1 @ self.value_y
        temp2 = np.max(self.A2 @ self.value_x + self.B2 @ self.value_y - self.b2[:, 0])
        # check optimality
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y)
        objctvLL = self.d2 @ y
        cstsLL = [
            x == self.value_x,
            self.ymin <= y, y <= self.ymax,
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0]
        ]
        prblLL = cp.Problem(cp.Maximize(objctvLL), cstsLL)
        prblLL.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
        temp3 = objctvLL.value - self.d2 @ self.value_y
        temp4 = np.max(self.A1 @ self.value_x - self.b1[:, 0])  #  + self.B1 @ y.value
        temp5 = self.c @ self.value_x + self.d1 @ y.value
        # print
        if temp1 > 0:
            print('Upper-level constraints are violated:', round(temp1, 4))
        if temp2 > 0:
            print('Lower-level constraints are violated:', round(temp2, 4))
        if temp3 > 0:
            print('Optimality are violated:', round(float(temp3), 4))
        if (temp1 <= 0) & (temp2 <= 0) & (temp3 <= 0):
            print('Constraints are satisfied')
            self.flag = 'solved optimal & checked feasible'
            self.UB = min(self.UB, self.value_objctv)
        else:
            # print('Fix x and solve y - Real objective:', round(float(temp5), 4))
            if temp4 > 0:
                print('Real upper-level constraints are violated:', round(temp4, 4))
            self.flag = 'resolved feasible'
            self.value_y = y.value
            self.value_objctv = float(temp5)
            self.UB = min(self.UB, self.value_objctv)
        return

    def solutionPrint(self):
        print('\nSolution:')
        print(self.flag)
        print('cost =', round(self.value_objctv, 2))
        print('x =', np.int_(self.value_x))
        print('y =', np.round(self.value_y, 2))
        print('Time =', round(self.time_total, 2), 's')
        print('Sample Time =', round(self.time_sampling, 2), 's')
        print('Training Time =', round(self.time_training, 2), 's')
        print('Solution Time =', round(self.time_solving, 2), 's')
        # print('lower bound =', round(self.LB, 2))
        # print('upper bound =', round(self.UB, 2))

    def solutionSave(self, Ind_iter):
        self.solutionHistory += [
            self.value_x, self.value_y, [self.value_objctv], [None],
            [self.time_total], [self.time_sampling], [self.time_training], [self.time_solving],
            [self.flag], ['^^^ iteration ' + str(Ind_iter+1) + ' ^^^'], [None]
       ]

class InstanceMILP(object):
    def __init__(self, num_x, num_y, num_cstsUL, num_cstsLL):
        """
        min  c*x+d1*y
        s.t.    A1*x<=b1 # + B1*y
                x in {0, 1}
                y = arg max d2*y
                            s.t.    A2*x+B2*y<=b2
                                    ymin<=y<=ymax
        """
        # parameter setting
        self.num_x = num_x
        self.num_y = num_y
        self.num_cstsUL = num_cstsUL
        self.num_cstsLL = num_cstsLL

        self.cmax = 100
        self.dmax = 100
        self.ABmax = 10 * 20 / (self.num_x + self.num_y)
        self.b1min = 10
        self.b1max = 110
        self.b2min = 30
        self.b2max = 130
        self.ymax=1
        self.ymin=0

        # self.c, self.d1, self.d2, self.A1, self.B1, self.b1, self.A2, self.B2, self.b2, self.bp = self.InstanceRead('InstanceLP.xlsx')
        self.c, self.d1, self.d2, self.A1, self.B1, self.b1, self.A2, self.B2, self.b2, self.bp = self.InstanceRead('InstanceLP_x'+str(num_x)+'y20.xlsx')

        self.time_total = 0
        self.time_sampling = 0
        self.time_training = 0
        self.time_solving = 0
        self.value_x = None
        self.value_y = None
        self.value_objctv = None
        self.UB = float('inf')
        self.LB = -float('inf')
        self.flag = 'unsolved'
        self.num_iter_enhanced = 3
        self.solutionHistory = []

    def InstanceRead(self, FileName):
        instance = pd.read_excel(io=FileName, sheet_name=None, header=None)
        c = instance['c'].values
        d1 = instance['d1'].values
        d2 = instance['d2'].values
        A1 = instance['A1'].values
        B1 = instance['B1'].values
        b1 = instance['h1'].values
        A2 = instance['A2'].values
        B2 = instance['B2'].values
        b2 = instance['h2'].values
        temp = instance['y'].values
        self.ymax = temp[0, 0]
        self.ymin = temp[1, 0]
        self.num_x = len(A2[0, :])
        self.num_y = len(B2[0, :])
        self.num_cstsUL = len(A1[:, 0])
        self.num_cstsLL = len(A2[:, 0])
        bp = self.InstanceBuild(c, d1, d2, A1, B1, b1, A2, B2, b2)
        return c, d1, d2, A1, B1, b1, A2, B2, b2, bp

    def InstanceBuild(self, c, d1, d2, A1, B1, b1, A2, B2, b2):
        bp = pe.ConcreteModel()
        bp.x = pe.Var(range(self.num_x), within=pe.Binary)
        bp.y = pe.Var(range(self.num_y), within=pe.Integers, bounds=(self.ymin, self.ymax))
        # Upper level
        bp.objctv = pe.Objective(expr=c[0, :] @ bp.x + d1[0, :] @ bp.y, sense=pe.minimize)
        bp.cstsUL = pe.ConstraintList()
        for i in range(self.num_cstsUL):
            bp.cstsUL.add(expr=A1[i, :] @ bp.x <= b1[i, 0])  #  + B1[i, :] @ bp.y
        # Lower level - declaration
        bp.LL = pao.SubModel(fixed=bp.x)
        bp.LL.objctv = pe.Objective(expr=d2[0, :] @ bp.y, sense=pe.maximize)
        bp.LL.cstsLL = pe.ConstraintList()
        for i in range(self.num_cstsLL):
            bp.LL.cstsLL.add(expr=A2[i, :] @ bp.x + B2[i, :] @ bp.y <= b2[i, 0])
        return bp

    def solve(self, solverName):
        if solverName == 'HPR':
            self.solveByHPR()
        elif solverName in ['FA', 'REG', 'PCCG', 'MIBS']:
            self.solveBySolver(solverName)
        elif solverName in ['GNN', 'ISNN']:
            # self.solveByNN(solverName)
            self.solveByNNEnhanced(solverName)
        return

    def solveByHPR(self):
        # model
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y, integer=True)
        objctv = self.c @ x + self.d1 @ y
        csts = [
            self.ymin <= y, y <= self.ymax,
            self.A1 @ x <= self.b1[:, 0],  # + self.B1 @ y
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0]
        ]

        # solve
        prbl = cp.Problem(cp.Minimize(objctv), csts)
        T1 = time.time()
        prbl.solve(solver=cp.GUROBI, verbose=False)  # , threads=4

        # save results
        if prbl.status != 'optimal':
            self.flag = 'infeasible'
            self.solutionPrint()
        else:
            self.flag = 'solved optimal'
            self.value_x = x.value
            self.value_y = y.value
            self.value_objctv = objctv.value[0]
            self.LB = max(self.LB, self.value_objctv)
            self.solutionCheck()
            T2 = time.time()
            self.time_total = T2 - T1
            self.time_solving = T2 - T1
            self.solutionPrint()
        return

    def solveBySolver(self, solverName):
        # solve
        T1 = time.time()
        with pao.Solver('pao.pyomo.' + solverName) as solver:
            results = solver.solve(self.bp, tee=True)  # , options={'threads': 4}

        # save results
        if results.solver.best_feasible_objective == None:
            self.flag = 'infeasible'
            self.solutionPrint()
        else:
            self.flag = 'solved optimal'
            value_x = []
            for i in self.bp.x:
                value_x.append(pe.value(self.bp.x[i]))
            value_x = np.array(value_x)
            value_y = []
            for i in self.bp.y:
                value_y.append(pe.value(self.bp.y[i]))
            value_y = np.array(value_y)
            value_objctv = pe.value(self.bp.objctv)
            self.value_x = value_x
            self.value_y = value_y
            self.value_objctv = value_objctv
            self.solutionCheck()
            T2 = time.time()
            self.time_total = T2-T1
            self.time_solving = T2-T1
            self.LB = max(self.LB, self.value_objctv)
            self.solutionPrint()
        return

    def solveByNN(self, solverName, num_samples=1000):
        # parameter
        flag_ISNN = True if solverName == 'ISNN' else False
        flag_doubleX = flag_ISNN & True
        self.solveByHPR()
        value_x = np.int_(self.value_x)
        value_y = np.int_(self.value_y)
        value_objctv = self.value_objctv

        # sampling
        T1 = time.time()
        num_samples = min(num_samples, 2 ** self.num_x)
        samples = self.samplesGen(num_samples)
        # samples = self.samplesRead('SamplesLP.xlsx')
        num_samples_obtained = len(samples[:, 0])
        T3 = time.time()

        # training
        num_layer = 2
        num_input = self.num_x * (2 if flag_doubleX == True else 1)
        num_hidden = calculateNumHidden(num_samples_obtained, num_layer, num_input, flag_ISNN)
        num_output = 1
        NNArchitecture = [num_input, num_hidden, num_hidden, num_output]
        NN = NNmodel(NNArchitecture, flag_ISNN, flag_doubleX)
        NN.train(samples[:, 0:-1])
        # NN.readParameters('NNparametersISNN.xlsx' if NN.flag_ISNN else 'NNparametersGNN.xlsx')
        T4 = time.time()

        # solving
        self.solveByGNN(NN)
        self.solutionCheck()
        self.solutionPrint()
        if self.value_objctv > value_objctv:
            self.value_x = value_x
            self.value_y = value_y
            self.value_objctv = value_objctv
        else:
            value_x = np.int_(self.value_x)
            value_y = np.int_(self.value_y)
            value_objctv = self.value_objctv
        if self.value_objctv > min(samples[:,-1]):
            idx = np.argmin(samples[:, -1])
            self.value_x = np.int_(samples[idx, 0:self.num_x])
            self.value_objctv = samples[idx, self.num_x+1]
            self.solutionCheck()
            self.flag = 'optimal in samples'
        T2 = time.time()
        self.time_total = T2 - T1
        self.time_sampling = T3 - T1
        self.time_training = T4 - T3
        self.time_solving = T2 - T4
        self.solutionPrint()

        return

    def solveByNNEnhanced(self, solverName, num_samples=1000):
        # parameter
        flag_ISNN = True if solverName == 'ISNN' else False
        flag_doubleX = flag_ISNN & True

        self.solveByHPR()
        value_x = self.value_x
        value_y = self.value_y
        value_objctv = self.value_objctv
        NN = None
        num_sampling = num_samples * 10
        max_repeated = 1000
        samples_all = np.zeros((0, self.num_x+2))
        for Ind_iter in range(self.num_iter_enhanced):
            # sampling
            T1 = time.time()
            samples = self.samplesGenEnhanced(num_samples, self.UB, NN, num_sampling, max_repeated)
            # samples = self.samplesRead('SamplesLP.xlsx')
            if len(samples) == 0:
                self.flag = 'insufficient samples'
                self.solutionSave(Ind_iter)
                break
            samples_all = np.vstack([samples_all, samples])
            samples_all = np.unique(samples_all, axis=0)
            num_samples_all = len(samples_all[:, 0])
            self.samplesSave(samples_all)
            T3 = time.time()
            self.time_sampling += T3-T1

            # training
            num_layer = 2
            num_input = self.num_x * (2 if flag_doubleX == True else 1)
            num_hidden = calculateNumHidden(num_samples_all, num_layer, num_input, flag_ISNN)
            num_output = 1
            NNArchitecture = [num_input, num_hidden, num_hidden, num_output]
            NN = NNmodel(NNArchitecture, flag_ISNN, flag_doubleX)
            NN.train(samples_all[:, 0:-1])  # -num_samples
            # NN.readParameters('NNparametersISNN.xlsx' if NN.flag_ISNN else 'NNparametersGNN.xlsx')
            T4 = time.time()
            self.time_training += T4-T3

            # solving
            self.solveByGNN(NN)
            self.solutionCheck()
            self.solutionPrint()
            if self.value_objctv > value_objctv:
                self.value_x = value_x
                self.value_y = value_y
                self.value_objctv = value_objctv
            else:
                value_x = self.value_x
                value_y = self.value_y
                value_objctv = self.value_objctv
            if self.value_objctv > min(samples_all[:,-1]):
                idx = np.argmin(samples_all[:, -1])
                self.value_x = samples_all[idx, 0:self.num_x]
                self.value_objctv = samples_all[idx, self.num_x+1]
                self.solutionCheck()
                self.flag = 'optimal in samples'
            T2 = time.time()
            self.time_solving += T2-T4
            self.time_total = self.time_sampling + self.time_training + self.time_solving
            self.solutionPrint()
            self.solutionSave(Ind_iter)

        return

    def solveByGNN(self, NN):
        # parameters
        bigM = 10

        # model
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y, integer=True)
        phi = cp.Variable()
        z = []
        z_temp = []
        z_sign = []
        for i in range(NN.num_layer_hidden + 2):
            z += [cp.Variable(NN.Architecture[i])]
            z_temp += [cp.Variable(NN.Architecture[i])]
            z_sign += [cp.Variable(NN.Architecture[i], boolean=True)]
        objctv = self.c @ x + self.d1 @ y
        csts = [
            self.ymin <= y, y <= self.ymax,
            self.A1 @ x <= self.b1[:, 0],  # + self.B1 @ y
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0],
            self.d2 @ y >= phi,
            z[-1] * (NN.label_max - NN.label_min) + NN.label_min == phi
        ]
        if NN.flag_doubleX:
            csts += [z[0] == cp.hstack([x, 1 - x])]
        else:
            csts += [z[0] == x]
        for i in range(NN.num_layer_hidden + 1):
            if i == 0:
                csts += [
                    z_temp[i+1] == NN.w[i] @ z[i] + NN.b[i][:, 0],
                    0 <= z[i+1], z[i+1] <= bigM * z_sign[i+1],
                    z_temp[i+1] <= z[i+1], z[i+1] <= z_temp[i+1] + bigM * (1 - z_sign[i+1])
                ]
            else:
                csts += [
                    z_temp[i+1] == NN.w[i] @ cp.hstack([z[i], z[0]]) + NN.b[i][:, 0],
                    0 <= z[i+1], z[i+1] <= bigM * z_sign[i+1],
                    z_temp[i+1] <= z[i+1], z[i+1] <= z_temp[i+1] + bigM * (1 - z_sign[i+1])
                ]

        # solve
        prbl = cp.Problem(cp.Minimize(objctv), csts)
        prbl.solve(solver=cp.GUROBI, verbose=True)  # , threads=4

        # save results
        if prbl.status != 'optimal':
            self.flag = 'infeasible'
        else:
            self.flag = 'solved optimal'
            self.value_x = x.value
            self.value_y = y.value
            self.value_objctv = objctv.value[0]
        return

    def samplesRead(self, FileName):
        data = pd.read_excel(io=FileName, sheet_name=None, header=None)
        samples = data['samples'].values
        return samples

    def samplesGen(self, num_samples, num_sampling=10000, max_repeated=1000):
        def BE(num_x, i):
            strx = '{:0' + str(num_x) + 'b}'
            ii = strx.format(i)
            sample = []
            for iii in range(num_x):
                sample.append(int(ii[iii]))
            return sample

        # lower-level problem
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y, integer=True)
        objctv = self.d2 @ y
        csts = [
            self.ymin <= y, y <= self.ymax,
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0]
        ]
        # sampling
        samples = []
        UBlist = []
        if 2**self.num_x <= num_samples:
            for i in range(2**self.num_x):
                sample = BE(self.num_x, i)
                prbl = cp.Problem(cp.Maximize(objctv), csts+[x == sample])
                prbl.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
                phi = objctv.value[0] if prbl.status == 'optimal' else None
                if phi == None:
                    print(i+1, '/', 2**self.num_x, ': Infeasible')
                    continue
                UB = self.c @ sample + self.d1 @ y.value
                UBlist.append(UB)
                samples.append(list(sample)+[phi]+list(UB))
                print(i+1, '/', 2**self.num_x, ', Optimal (count_samples=', len(samples), 'UB=', UB, ')')
        else:
            record = []
            max_iter = num_sampling
            count_repeated = 0
            for i in range(max_iter):
                if (len(record) >= 2**self.num_x) | (count_repeated > max_repeated):
                    break
                temp = int(np.round(np.random.rand() * (2**self.num_x-1)))
                if temp in record:
                    count_repeated += 1
                    print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', repeated')
                    continue
                else:
                    count_repeated = 0
                    record.append(temp)
                sample = BE(self.num_x, temp)
                prbl = cp.Problem(cp.Maximize(objctv), csts+[x == sample])
                prbl.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
                phi = objctv.value[0] if prbl.status == 'optimal' else None
                if phi == None:
                    print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', Infeasible')
                    continue
                UB = self.c @ sample + self.d1 @ y.value
                UBlist.append(UB)
                samples.append(list(sample)+[phi]+list(UB))
                print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', Optimal (count_samples=', len(samples), 'UB=', UB, ')')
                if len(samples) >= num_samples:
                    break
        # export samples
        print(min(UBlist))
        self.samplesSave(samples)
        self.samplesPrint(samples)
        return np.array(samples)

    def samplesGenEnhanced(self, num_samples, UB, NN=None, num_sampling=10000, max_repeated=1000):
        # parameters
        bigM = 10
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y, integer=True)

        # sampling problem
        csts0 = [
            self.ymin <= y, y <= self.ymax,
            self.A1 @ x <= self.b1[:, 0],  # + self.B1 @ y
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0],
            self.c @ x + self.d1 @ y <= UB,
        ]
        # if NN == None:
        #     if UB != float('inf'):
        #         csts0 += [
        #             self.c @ x + self.d1 @ y <= UB,
        #         ]
        # else:
        #     phi = cp.Variable()
        #     z = []
        #     z_temp = []
        #     z_sign = []
        #     for i in range(NN.num_layer_hidden + 2):
        #         z += [cp.Variable(NN.Architecture[i])]
        #         z_temp += [cp.Variable(NN.Architecture[i])]
        #         z_sign += [cp.Variable(NN.Architecture[i], boolean=True)]
        #     csts0 += [
        #         self.c @ x + self.d1 @ y + 1 * (phi - self.d2 @ y) <= UB,
        #         z[-1] * (NN.label_max - NN.label_min) + NN.label_min == phi
        #     ]
        #     if NN.flag_doubleX:
        #         csts0 += [z[0] == cp.hstack([x, 1 - x])]
        #     else:
        #         csts0 += [z[0] == x]
        #     for i in range(NN.num_layer_hidden + 1):
        #         if i == 0:
        #             csts0 += [
        #                 z_temp[i+1] == NN.w[i] @ z[i] + NN.b[i][:, 0],
        #                 0 <= z[i+1], z[i+1] <= bigM * z_sign[i+1],
        #                 z_temp[i+1] <= z[i+1], z[i+1] <= z_temp[i+1] + bigM * (1 - z_sign[i+1])
        #             ]
        #         else:
        #             csts0 += [
        #                 z_temp[i+1] == NN.w[i] @ cp.hstack([z[i], z[0]]) + NN.b[i][:, 0],
        #                 0 <= z[i+1], z[i+1] <= bigM * z_sign[i+1],
        #                 z_temp[i+1] <= z[i+1], z[i+1] <= z_temp[i+1] + bigM * (1 - z_sign[i+1])
        #             ]

        # lower-level problem
        objctv = self.d2 @ y
        csts = [
            self.ymin <= y, y <= self.ymax,
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0]
        ]

        # sampling
        samples = []
        record = []
        UBlist = []
        max_iter = num_sampling
        count_repeated = 0
        count_infeasible = 0
        for i in range(max_iter):
            if (len(record) >= 2**self.num_x) | (count_repeated > max_repeated) | (count_infeasible > max_repeated/2):
                break
            h = 2 * np.random.rand(1, self.num_x) - 1
            D = np.diag(np.random.rand(self.num_x))
            U = orth(np.random.rand(self.num_x, self.num_x))
            Q = U.T @ D @ U
            objctv0 = h @ x + x.T @ cp.psd_wrap(Q) @ x
            prbl0 = cp.Problem(cp.Minimize(objctv0), csts0)
            prbl0.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
            if prbl0.status != 'optimal':
                print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', ' Infeasible')
                count_infeasible += 1
                continue
            sample = np.int_(x.value)
            temp = 2**np.array(range(self.num_x)) @ sample
            if temp in record:
                count_repeated += 1
                print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', repeated')
                continue
            else:
                count_repeated = 0
                record.append(temp)
            prbl = cp.Problem(cp.Maximize(objctv), csts+[x == sample])
            prbl.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
            phi = objctv.value[0] if prbl.status == 'optimal' else None
            if phi == None:
                print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', Infeasible')
                continue
            UB = self.c @ sample + self.d1 @ y.value
            UBlist.append(UB)
            samples.append(list(sample)+[phi]+list(UB))
            print(len(record), '/', 2**self.num_x, '|', i+1, '/', max_iter, ':', temp, ', Optimal (count_samples=', len(samples), 'UB=', UB, ')')
            count_infeasible = 0
            if len(samples) >= num_samples:
                break
        # export samples
        if len(UBlist)==0:
            return np.zeros((0, self.num_x+2))
        print(min(UBlist))
        self.samplesSave(samples)
        self.samplesPrint(samples)
        return np.array(samples)

    def samplesPrint(self, samples):
        zz = []
        for i in range(len(samples)):
            if samples[i][self.num_x] not in zz:
                zz.append(samples[i][self.num_x])
        zz.sort()
        print(zz[0], '-', zz[-1])
        plt.figure()
        plt.plot(zz)
        plt.title('sample_value')
        plt.show()

    def samplesSave(self, samples):
        FileName = 'SamplesLP.xlsx'
        writer = pd.ExcelWriter(FileName)
        wrt = pd.DataFrame(samples)
        wrt.to_excel(writer, 'samples', header=None, index=False)
        writer.close()
        print('successfully export samples as ', FileName)

    def solutionCheck(self):
        print('cost =', round(self.value_objctv, 2))
        # check feasibility
        temp1 = np.max(self.A1 @ self.value_x - self.b1[:, 0])  # + self.B1 @ self.value_y
        temp2 = np.max(self.A2 @ self.value_x + self.B2 @ self.value_y - self.b2[:, 0])
        # check optimality
        x = cp.Variable(self.num_x, boolean=True)
        y = cp.Variable(self.num_y, integer=True)
        objctvLL = self.d2 @ y
        cstsLL = [
            x == self.value_x,
            self.ymin <= y, y <= self.ymax,
            self.A2 @ x + self.B2 @ y <= self.b2[:, 0]
        ]
        prblLL = cp.Problem(cp.Maximize(objctvLL), cstsLL)
        prblLL.solve(solver=cp.GUROBI, verbose=False)  # , threads=4
        temp3 = objctvLL.value - self.d2 @ self.value_y
        temp4 = np.max(self.A1 @ self.value_x - self.b1[:, 0])  #  + self.B1 @ y.value
        temp5 = self.c @ self.value_x + self.d1 @ y.value
        # print
        if temp1 > 0:
            print('Upper-level constraints are violated:', round(temp1, 4))
        if temp2 > 0:
            print('Lower-level constraints are violated:', round(temp2, 4))
        if temp3 > 0:
            print('Optimality are violated:', round(float(temp3), 4))
        if (temp1 <= 0) & (temp2 <= 0) & (temp3 <= 0):
            print('Constraints are satisfied')
            self.flag = 'solved optimal & checked feasible'
            self.UB = min(self.UB, self.value_objctv)
        else:
            # print('Fix x and solve y - Real objective:', round(float(temp5), 4))
            if temp4 > 0:
                print('Real upper-level constraints are violated:', round(temp4, 4))
            self.flag = 'resolved feasible'
            self.value_y = y.value
            self.value_objctv = float(temp5)
            self.UB = min(self.UB, self.value_objctv)
        return

    def solutionPrint(self):
        print('\nSolution:')
        print(self.flag)
        print('cost =', round(self.value_objctv, 2))
        print('x =', np.int_(self.value_x))
        print('y =', np.int_(self.value_y))
        print('Time =', round(self.time_total, 2), 's')
        print('Sample Time =', round(self.time_sampling, 2), 's')
        print('Training Time =', round(self.time_training, 2), 's')
        print('Solution Time =', round(self.time_solving, 2), 's')
        # print('lower bound =', round(self.LB, 2))
        # print('upper bound =', round(self.UB, 2))

    def solutionSave(self, Ind_iter):
        self.solutionHistory += [
            self.value_x, self.value_y, [self.value_objctv], [None],
            [self.time_total], [self.time_sampling], [self.time_training], [self.time_solving],
            [self.flag], ['^^^ iteration ' + str(Ind_iter+1) + ' ^^^'], [None]
       ]
