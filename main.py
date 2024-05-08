from Instance import *
import openpyxl

list_num_x = [50,60] #10, 20,
list_solver = ['GNN','ISNN']  #,  'HPR', 'MIBS'
for Ind_num_x in range(len(list_num_x)):
# Generate Instance
    num_x = list_num_x[Ind_num_x]
    num_cstsUL = int(num_x * 1)
    num_y = 20  # num_x
    num_cstsLL = int(num_y * 1)

    for Ind_solver in range(len(list_solver)):
        # solve instance
        results = []
        solverName = list_solver[Ind_solver]  # MIBS, GNN, ISNN
        num_run = 10 if solverName in ['GNN', 'ISNN'] else 1
        for Ind_run in range(num_run):
            print('***********run'+str(Ind_run+1)+'***********')
            # instance = InstanceLP(num_x, num_y, num_cstsUL, num_cstsLL)
            # ResultsFileName = 'resultsLP.xlsx'
            instance = InstanceMILP(num_x, num_y, num_cstsUL, num_cstsLL)
            ResultsFileName = 'resultsMILP.xlsx'
            instance.solve(solverName)
            results += [
                        ['************************** run ' + str(Ind_run+1) + ' **************************']
                   ]
            results += instance.solutionHistory

        # save data
        workbook = openpyxl.load_workbook(ResultsFileName)
        SheetName = 'n=' + str(num_x) + '_by' + solverName
        if SheetName in workbook.sheetnames:
            workbook.remove(workbook[SheetName])
            workbook.save(ResultsFileName)
        writer = pd.ExcelWriter(ResultsFileName, mode='a', engine='openpyxl')
        wrt = pd.DataFrame(results)
        wrt.to_excel(writer, 'n=' + str(num_x) + '_by' + solverName, header=None, index=False)
        print('successfully export results')
        writer.close()
