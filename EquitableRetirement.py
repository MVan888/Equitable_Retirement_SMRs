# -*- coding: utf-8 -*-
"""
Created on Mon May 10 23:25:12 2021

@author: bhavrathod
"""
import numpy as np
import pandas as pd
import pyomo.environ as pe
import pyomo.opt
# Added BR 6/21/21
from pyomo.opt import SolverStatus

import warnings
warnings.filterwarnings("ignore")

class EquitableRetirement:
    
    # Parameters from problem formulation
    class Params:
        def __init__(self):
            # parameters
            self.HISTGEN = None 
            self.COALCAP = None
            self.CF = None 
            self.RECAPEX = None  
            self.REFOPEX = None
            self.REVOPEX = None #____________________
            self.COALVOPEX = None 
            self.COALFOPEX = None
            self.MAXCAP = None 
            self.SITEMAXCAP = None
            self.SITEMINCAP = None #_____________
            self.MAXSITES = None
            self.HD = None
            self.RETEF = None
            self.CONEF = None
            self.COALOMEF = None
            self.REOMEF = None
    
    # List of decision variables that we care about
    class Output:
        def __init__(self):
            self.Z = None
            self.capInvest = None
            self.capRetire = None 
            self.reGen = None
            self.coalGen = None
            self.reCap = None
            self.reInvest = None
            self.coalRetire = None
            self.reOnline = None
            self.coalOnline = None
    
    # Called when class is created. Create sets for years, coal plants and RE sites. Then instantiate Params and Output.
    def __init__(self):
        # sets
        self.Y = None
        self.C = None
        self.R = None 

        self.Params = EquitableRetirement.Params()
        self.Output = EquitableRetirement.Output()
    
    
    def __buildModel(self,alpha,beta,gamma,DiscRate):

        ######### helper function ##########
        
        def a2d(data, *sets): 
            '''
            This function converts 1 or 2 dimension arrays into dictionaries compatible with pyomo set/param initializers
            '''
            if isinstance(data, pd.Series):
                data = data.values
            if isinstance(data, int):
                data = [data]
            if isinstance(data, list):
                data = np.array(data)

            # Ensure data dimensions are <= 2.
            assert(data.ndim <= 2)

            # direct indexing
            # *sets is an optional arguement which may or may not be provided.
            if len(sets) == 0:
                if data.ndim == 1:
                    return {i:data[i] for i in range(len(data))}
                else:
                    return {(i,j):data[i,j] for i in range(len(data[:,0])) for j in range(len(data[0,:]))}

            # otherwise use sets
            assert(len(sets) == data.ndim)

            if data.ndim == 1:
                return {sets[0][i]:data[i] for i in range(len(data))}

            if data.ndim == 2:
                return {(sets[0][i],sets[1][j]):data[i,j] for i in range(len(sets[0])) for j in range(len(sets[1]))} 
        
        ############ end helper ############
        
        self.NUM_RE = len(self.R)
        self.NUM_COAL = len(self.C)
        self.NUM_YEARS = len(self.Y)
        
        # fill model
        model = pe.ConcreteModel()

        # sets that form basis for the formulation.
        model.Y = pe.Set(initialize=self.Y, doc = "Years of program") 
        model.C = pe.Set(initialize=self.C, doc = "Coal Plant IDs")
        model.R = pe.Set(initialize=self.R, doc='Renewable plant locations with type of technology (wind or solar)')
        
        ## Sets are entered into pe.XXX() as parent set last. So model.R, model.C means for each coal plant, each RE plant.
        # parameters: set the param is based on, param dictionary values, and documentation.
        model.HISTGEN = pe.Param(model.C, initialize=a2d(self.Params.HISTGEN,self.C), doc = "Historical Generation of coal plants")
        model.COALCAP = pe.Param(model.C, initialize=a2d(self.Params.COALCAP,self.C), doc = 'Nameplate Capacity of coal plants')
        model.CF = pe.Param(model.R, initialize=a2d(self.Params.CF,self.R),doc = "Annual CF @ RE location")
        model.RECAPEX = pe.Param(model.R, initialize=a2d(self.Params.RECAPEX,self.R),doc = "RE plants CAPEX values ($/MW")
        model.REFOPEX = pe.Param(model.R, initialize=a2d(self.Params.REFOPEX,self.R),doc = "RE plants OPEX values ($/MW")
        # MWh-->MW
        model.REVOPEX = pe.Param(model.R, initialize=a2d(self.Params.REVOPEX,self.R),doc = "RE plants VOPEX values ($/MWh")
        # NEW^
        model.COALVOPEX = pe.Param(model.C, initialize=a2d(self.Params.COALVOPEX,self.C), doc = 'Coal plants VOPEX values $/MWh')
        model.COALFOPEX = pe.Param(model.C, initialize=a2d(self.Params.COALFOPEX,self.C), doc = "Coal plants FOPEX values $/MW")
        model.MAXCAP = pe.Param(model.R,model.C,initialize=a2d(self.Params.MAXCAP,self.R,self.C), doc ='Maximum capacity for RE plant to replace coal plant MW')    # Multiple sets as basis for values.
        model.SITEMAXCAP = pe.Param(model.R, initialize=a2d(self.Params.SITEMAXCAP,self.R), doc = 'Maximum total capacity for RE site MW')
        
        model.SITEMINCAP = pe.Param(model.R, initialize=a2d(self.Params.SITEMINCAP,self.R), doc = 'Maximum total capacity for RE site MW')
        
        
        model.MAXSITES = pe.Param(model.C,initialize=a2d(self.Params.MAXSITES,self.C), doc = "Number of Sites allowable to replace coal plant")
        model.HD = pe.Param(model.C,initialize=a2d(self.Params.HD,self.C), doc="Health damages of each coal plant")
        model.RETEF = pe.Param(model.C,initialize=a2d(self.Params.RETEF,self.C), doc="Retirement EF for each coal plant (will most likely be a single static value)")
        model.CONEF = pe.Param(model.R,model.Y,initialize=a2d(self.Params.CONEF,self.R,self.Y),doc="Construction/installation EFs for RE plants")
        model.COALOMEF = pe.Param(model.C,initialize=a2d(self.Params.COALOMEF,self.C),doc="O&M EF for coal plants (will be most likely be a static value as well)")
        model.REOMEF = pe.Param(model.R,model.Y,initialize=a2d(self.Params.REOMEF,self.R,self.Y),doc="O&M EF for RE plants jobs/MW")
        
        # variables: Total number of decision variables is defined by multiplying the sets provided upfront.
        model.capInvest = pe.Var(model.R,model.C,model.Y,within=pe.NonNegativeReals, doc = "Capacity to be invested in that renewable plant to replace coal")   # For each Y, for each C, for each R there is a capInvest decision variable.
        model.capRetire = pe.Var(model.C,model.Y,within=pe.NonNegativeReals,doc = "amount of capacity to be retired for each coal plant")
        model.reGen = pe.Var(model.R,model.C,model.Y,within=pe.NonNegativeReals, doc = "RE generation at each plant")
        model.coalGen = pe.Var(model.C,model.Y,within=pe.NonNegativeReals, doc = "Coal generation for each plant")
        model.reCap = pe.Var(model.R,model.C,model.Y,within=pe.NonNegativeReals, doc = "Capacity size for each RE plant")
        model.reInvest = pe.Var(model.R,model.C,model.Y,within=pe.Binary, doc = "Binary variable to invest in RE to replace coal")
        model.coalRetire = pe.Var(model.C,model.Y,within=pe.Binary, doc = "Binary variable to retire coal plant")
        model.reOnline = pe.Var(model.R,model.C,model.Y,within=pe.Binary, doc = "Binary variable of whether the RE plant is on (1) or off (0)")
        model.coalOnline = pe.Var(model.C,model.Y,within=pe.Binary, doc = "Binary variable of whether the coal plant is on (1) or off (0)")
        
        # objective: Combination of parameters and variables over sets.
        def SystemCosts(model):
            return sum(sum(model.COALFOPEX[c] * model.COALCAP[c] * model.coalOnline[c,y] for c in model.C)/((1+DiscRate)**y) for y in model.Y) \
                + sum(sum(model.COALVOPEX[c] * model.coalGen[c,y] for c in model.C)/((1+DiscRate)**y) for y in model.Y) \
                + sum(sum(sum(model.REFOPEX[r] * model.reCap[r,c,y] for r in model.R) for c in model.C)/((1+DiscRate)**y) for y in model.Y) \
                + sum(sum(sum(model.RECAPEX[r] * model.capInvest[r,c,y] for r in model.R) for c in model.C)/((1+DiscRate)**y) for y in model.Y) \
                + sum(sum(sum(model.REVOPEX[r] * model.reGen[r,c,y] for r in model.R) for c in model.C)/((1+DiscRate)**y) for y in model.Y)     # __________________________

        def HealthCosts(model):
            return sum(sum(model.HD[c]*model.coalGen[c,y] for c in model.C)/((1+DiscRate)**y) for y in model.Y)

        def Jobs(model):
            #first coal retire + coal operation then + RE construction + RE O&M
            return sum(sum(model.RETEF[c]*model.capRetire[c,y] for c in model.C)/((1+DiscRate)**y) for y in model.Y) \
                + sum(sum(model.COALOMEF[c]*model.coalGen[c,y] for c in model.C)/((1+DiscRate)**y) for y in model.Y) \
                + sum(sum(sum(model.CONEF[r,y]*model.capInvest[r,c,y] + model.REOMEF[r,y]*model.reCap[r,c,y] for c in model.C) for r in model.R)/((1+DiscRate)**y) for y in model.Y) # reGen changed to reCap in alignment with the unit analysis behind jobs/MW versus jobs/MWh. MV 08092021

        def Z(model):
            return alpha*SystemCosts(model) + beta*HealthCosts(model) - gamma*Jobs(model)
        model.Z = pe.Objective(rule=Z, doc='Minimize system costs, health damages, while maximizing jobs')
        
        # constraints
        def coalGenRule(model,c,y):
            return model.coalGen[c,y] == model.HISTGEN[c]*model.coalOnline[c,y]
        model.coalGenRule = pe.Constraint(model.C,model.Y,rule=coalGenRule, doc='Coal generation must equal historical generation * whether that plant is online')

        def balanceGenRule(model,c,y):
            return sum(model.reGen[r,c,y] for r in model.R) == model.HISTGEN[c]-model.coalGen[c,y]
        model.balanceGenRule = pe.Constraint(model.C,model.Y,rule=balanceGenRule, doc = "RE generation for each coal location must equal retired capacity")

        def reGenRule(model,r,c,y):
            return model.reGen[r,c,y] == model.CF[r]*model.reCap[r,c,y]*8760 # changed to equality based on conversation to test: MV 08102021
        model.reGenRule = pe.Constraint(model.R,model.C,model.Y,rule=reGenRule, doc='RE generation must be less than or equal to capacity factor* chosen capacity *8760')

        def reCapRule(model,r,c,y):
            return model.reCap[r,c,y] <= model.MAXCAP[r,c]*model.reOnline[r,c,y]
        model.reCapRule = pe.Constraint(model.R,model.C,model.Y,rule=reCapRule, doc = "RE capacity decision variable should be less then or equal to max capacity* whether RE plant is online")

        def reCapLimit(model,r,y):
            return sum(model.reCap[r,c,y] for c in model.C) <= model.SITEMAXCAP[r]
        model.reCapLimit = pe.Constraint(model.R,model.Y,rule=reCapLimit, doc = "RE plants can not overcount towards multiple coal generators (sum of RE plant contribution to each coal plant <= max cap of RE plant)")
        
        #def reCapLimitLow(model,r,y):
        #    return sum(model.reCap[r,c,y] for c in model.C) >= model.SITEMINCAP[r]
        #model.reCapLimitLow = pe.Constraint(model.R,model.Y,rule=reCapLimitLow, doc = "")

        def capInvestRule(model,r,c,y):
            if y == model.Y[1]:
                return model.capInvest[r,c,y] == model.reCap[r,c,y]
            #else
            return model.capInvest[r,c,y] == model.reCap[r,c,y] - model.reCap[r,c,y-1]
        model.capInvestRule = pe.Constraint(model.R,model.C,model.Y,rule=capInvestRule, doc = "RE capacity to invest is equal to difference in RE cap across years")

        def capInvestLimit(model,r,c,y):
            return model.capInvest[r,c,y] <= model.MAXCAP[r,c]*model.reInvest[r,c,y]
        model.capInvestLimit = pe.Constraint(model.R,model.C,model.Y,rule=capInvestLimit, doc = "RE capacity to invest must be less than or equal to max cap of site, if we invest")

        def capRetireRule(model,c,y):
            return model.capRetire[c,y]  == model.COALCAP[c]*model.coalRetire[c,y]
        model.capRetireRule = pe.Constraint(model.C,model.Y,rule=capRetireRule, doc = "Retired coal capacity is equal to the whole cs capacity, if it is retired that year")

        def reInvestRule(model,r,c,y):
            if y == model.Y[1]:
                return model.reInvest[r,c,y] == model.reOnline[r,c,y]
            #else
            return model.reInvest[r,c,y] == model.reOnline[r,c,y] - model.reOnline[r,c,y-1]
        model.reInvestRule = pe.Constraint(model.R,model.C,model.Y,rule=reInvestRule,doc= "Decision to invest in RE is current year - prior")

        def reInvestLimit(model,c,y):
            return sum(model.reInvest[r,c,y] for r in model.R) <= model.MAXSITES[c] * model.coalRetire[c,y]
        model.reInvestLimit = pe.Constraint(model.C,model.Y,rule=reInvestLimit,doc = "Number of new RE sites must be less than or equal to max RE sites for that coal plant * whether we retire")

        def replacementSitesLimit(model,c,y):
            return sum(model.reInvest[r,c,y] for r in model.R) <= model.MAXSITES[c] * model.coalRetire[c,y]
        model.replacementSitesLimit = pe.Constraint(model.C,model.Y,rule=replacementSitesLimit,doc = "If a coal plant retires, the number of sites that can replace it are limited")

        def coalRetireRule(model,c,y):
            if y == model.Y[1]:
                return model.coalRetire[c,y] == 1 - model.coalOnline[c,y]
            #else
            return model.coalRetire[c,y] == model.coalOnline[c,y-1] - model.coalOnline[c,y]
        model.coalRetireRule = pe.Constraint(model.C,model.Y,rule=coalRetireRule, doc = "Coal retire activation is current year must prior year")
        
        self.model = model

    def solve(self,alpha,beta,gamma,DiscRate, solver='glpk'):
        '''solve(self,alpha,beta,gamma):
        Solve the equitable retirement optimization problem. PRECONDITION: All sets and params have been initialized.
        '''
        #rebuild model
        self.__buildModel(alpha,beta,gamma,DiscRate)

        print('running ({},{},{})...'.format(alpha,beta,gamma))
        
        opt = pyomo.opt.SolverFactory(solver)
        
        # Updated BR 6/21/21
        res = opt.solve(self.model)
        
        # self.model.pprint()
        
        # Added BR 6/21/21 http://www.pyomo.org/blog/2015/1/8/accessing-solver
        print('>>Solver status is {} and solver termination condition is {}'.format(res.solver.status,res.solver.termination_condition))

        # extract
        self.__extractResults()
    
    # Shorthand below.
    def __extractResults(self):
        self.Output.Z = round(pe.value(self.model.Z),2)
        self.Output.capInvest = np.array([[[pe.value(self.model.capInvest[r,c,y]) for y in self.Y] for c in self.C] for r in self.R])
        self.Output.capRetire = np.array([[pe.value(self.model.capRetire[c,y]) for y in self.Y] for c in self.C])
        self.Output.reGen = np.array([[[pe.value(self.model.reGen[r,c,y]) for y in self.Y] for c in self.C] for r in self.R])
        self.Output.coalGen = np.array([[pe.value(self.model.coalGen[c,y]) for y in self.Y] for c in self.C])
        self.Output.reCap = np.array([[[pe.value(self.model.reCap[r,c,y]) for y in self.Y] for c in self.C] for r in self.R])
        self.Output.reInvest = np.array([[[pe.value(self.model.reInvest[r,c,y]) for y in self.Y] for c in self.C] for r in self.R])
        self.Output.coalRetire = np.array([[pe.value(self.model.coalRetire[c,y]) for y in self.Y] for c in self.C])
        self.Output.reOnline = np.array([[[pe.value(self.model.reOnline[r,c,y]) for y in self.Y] for c in self.C] for r in self.R])
        self.Output.coalOnline = np.array([[pe.value(self.model.coalOnline[c,y]) for y in self.Y] for c in self.C])
        pass
