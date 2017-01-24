import numpy as np
import pandas as pd
import itertools
import pulp

USE_GUROBI = True

def do_inference_brute_force(ps, L, M, unary_params, pw_params, unary_features, pw_features, 
                             y_true=None, y_true_list=None, debug=False):
    """
    Inference using brute force search (for sanity check), could be:
    - Train/prediction inference for single-label SSVM
    - Train/prediction inference for multi-label SSVM
    """
    assert(L > 1)
    assert(L <= M)
    assert(ps >= 0)
    assert(ps < M)
    if y_true is not None: assert(y_true_list is not None and type(y_true_list) == list)
    
    Cu = np.zeros(M, dtype=np.float)      # unary_param[p] x unary_features[p]
    Cp = np.zeros((M, M), dtype=np.float) # pw_param[pi, pj] x pw_features[pi, pj]
    # a intermediate POI should NOT be the start POI, NO self-loops
    for pi in range(M):
        Cu[pi] = np.dot(unary_params[pi, :], unary_features[pi, :]) # if pi != ps else -np.inf
        for pj in range(M):
            Cp[pi, pj] = -np.inf if (pj == ps or pi == pj) else np.dot(pw_params[pi, pj, :], pw_features[pi, pj, :])
    
    max_score = 0
    y_best = None
    for x in itertools.permutations([p for p in range(M) if p != ps], int(L-1)):
        y = [ps] + list(x)
        score = 0
        
        if y_true is not None and np.any([np.all(np.array(y) == np.asarray(yj)) for yj in y_true_list]) == True: continue
        
        for j in range(1, L): score += Cp[y[j-1], y[j]] + Cu[y[j]]
        if y_true is not None: score += np.sum(np.asarray(y) != np.asarray(y_true))
        
        if score > max_score:
            max_score = score
            y_best = y
    if debug == True: print(max_score)
    return y_best



def do_inference_greedy(ps, L, M, unary_params, pw_params, unary_features, pw_features, y_true=None, y_true_list=None):
    """
    Inference using greedy search (baseline), could be:
    - Train/prediction inference for single-label SSVM
    - Prediction inference for multi-label SSVM
    """
    assert(L > 1)
    assert(L <= M)
    assert(ps >= 0)
    assert(ps < M)
    if y_true is not None:
        assert(y_true_list is not None and type(y_true_list) == list)
        assert(len(y_true_list) == 1)
    
    Cu = np.zeros(M, dtype=np.float)      # unary_param[p] x unary_features[p]
    Cp = np.zeros((M, M), dtype=np.float) # pw_param[pi, pj] x pw_features[pi, pj]
    # a intermediate POI should NOT be the start POI, NO self-loops
    for pi in range(M):
        Cu[pi] = np.dot(unary_params[pi, :], unary_features[pi, :]) # if pi != ps else -np.inf
        for pj in range(M):
            Cp[pi, pj] = -np.inf if (pj == ps or pi == pj) else np.dot(pw_params[pi, pj, :], pw_features[pi, pj, :])
    
    y_hat = [ps]
    for t in range(1, L):
        candidate_points = [p for p in range(M) if p not in y_hat]
        p = y_hat[-1]
        maxix = np.argmax([Cp[p, p1] + Cu[p1] + float(p1 != y_true[t]) if y_true is not None else \
                           Cp[p, p1] + Cu[p1] for p1 in candidate_points])
        y_hat.append(candidate_points[maxix])
        
    return np.asarray(y_hat)



def do_inference_viterbi(ps, L, M, unary_params, pw_params, unary_features, pw_features, y_true=None, y_true_list=None):
    """
    Inference using the Viterbi algorithm, could be:
    - Train/prediction inference for single-label SSVM
    - Prediction inference for multi-label SSVM
    """
    assert(L > 1)
    assert(L <= M)
    assert(ps >= 0)
    assert(ps < M)
    if y_true is not None:
        assert(y_true_list is not None and type(y_true_list) == list)
        assert(len(y_true_list) == 1)
    
    Cu = np.zeros(M, dtype=np.float)      # unary_param[p] x unary_features[p]
    Cp = np.zeros((M, M), dtype=np.float) # pw_param[pi, pj] x pw_features[pi, pj]
    # a intermediate POI should NOT be the start POI, NO self-loops
    for pi in range(M):
        Cu[pi] = np.dot(unary_params[pi, :], unary_features[pi, :]) # if pi != ps else -np.inf
        for pj in range(M):
            Cp[pi, pj] = -np.inf if (pj == ps or pi == pj) else np.dot(pw_params[pi, pj, :], pw_features[pi, pj, :])
    
    A = np.zeros((L-1, M), dtype=np.float)     # scores matrix
    B = np.ones((L-1, M), dtype=np.int) * (-1) # backtracking pointers
    
    for p in range(M): # ps--p
        A[0, p] = Cp[ps, p] + Cu[p]
        #if y_true is not None and p != ps: A[0, p] += float(p != y_true[1])/L  # loss term: normalised
        if y_true is not None and p != ps: A[0, p] += float(p != y_true[1])
        B[0, p] = ps

    for t in range(0, L-2):
        for p in range(M):
            #loss = float(p != y_true[l+2])/L if y_true is not None else 0  # loss term: normlised
            loss = float(p != y_true[t+2]) if y_true is not None else 0
            scores = [A[t, p1] + Cp[p1, p] + Cu[p] for p1 in range(M)] # ps~~p1--p
            maxix = np.argmax(scores)
            A[t+1, p] = scores[maxix] + loss
            #B[l+1, p] = np.array(range(N))[maxix]
            B[t+1, p] = maxix

    y_hat = [np.argmax(A[L-2, :])]
    p, t = y_hat[-1], L-2
    while t >= 0:
        y_hat.append(B[t, p])
        p, t = y_hat[-1], t-1
    y_hat.reverse()

    return np.asarray(y_hat)



def do_inference_ILP(ps, L, M, unary_params, pw_params, unary_features, pw_features, y_true=None, y_true_list=None):
    """
    Inference using integer linear programming (ILP), could be:
    - Train/prediction inference for single-label SSVM (NOTE: NOT Hamming loss)
    - Prediction inference for multi-label SSVM
    """
    assert(L > 1)
    assert(L <= M)
    assert(ps >= 0)
    assert(ps < M)
    if y_true is not None:
        assert(y_true_list is not None and type(y_true_list) == list)
        assert(len(y_true_list) == 1)

    p0 = str(ps)
    pois = [str(p) for p in range(M)] # create a string list for each POI
    pb = pulp.LpProblem('Inference_ILP', pulp.LpMaximize) # create problem
    # visit_i_j = 1 means POI i and j are visited in sequence
    visit_vars = pulp.LpVariable.dicts('visit', (pois, pois), 0, 1, pulp.LpInteger) 
    # isend_l = 1 means POI l is the END POI of trajectory
    isend_vars = pulp.LpVariable.dicts('isend', pois, 0, 1, pulp.LpInteger) 
    # a dictionary contains all dummy variables
    dummy_vars = pulp.LpVariable.dicts('u', [x for x in pois if x != p0], 2, M, pulp.LpInteger)
    
    # add objective
    objlist = []
    for pi in pois:     # from
        for pj in pois: # to
            objlist.append(visit_vars[pi][pj] * (np.dot(unary_params[int(pj)], unary_features[int(pj)]) + \
                                                 np.dot(pw_params[int(pi), int(pj)], pw_features[int(pi), int(pj)])))
    if y_true is not None: # Loss: normalised number of mispredicted POIs, Hamming loss is non-linear of 'visit'
        objlist.append(1)
        for j in range(M):
            pj = pois[j]
            for k in range(1, L): 
                pk = str(y_true[k])
                #objlist.append(-1.0 * visit_vars[pj][pk] / L) # loss term: normalised
                objlist.append(-1.0 * visit_vars[pj][pk])
    pb += pulp.lpSum(objlist), 'Objective'
    
    # add constraints, each constraint should be in ONE line
    pb += pulp.lpSum([visit_vars[pi][pi] for pi in pois]) == 0, 'NoSelfLoops'
    pb += pulp.lpSum([visit_vars[p0][pj] for pj in pois]) == 1, 'StartAt_p0'
    pb += pulp.lpSum([visit_vars[pi][p0] for pi in pois]) == 0, 'NoIncoming_p0'
    pb += pulp.lpSum([visit_vars[pi][pj] for pi in pois for pj in pois]) == L-1, 'Length'
    pb += pulp.lpSum([isend_vars[pi] for pi in pois]) == 1, 'OneEnd'
    pb += isend_vars[p0] == 0, 'StartNotEnd'
    
    for pk in [x for x in pois if x != p0]:
        pb += pulp.lpSum([visit_vars[pi][pk] for pi in pois]) == isend_vars[pk] + \
              pulp.lpSum([visit_vars[pk][pj] for pj in pois if pj != p0]), 'ConnectedAt_' + pk
        pb += pulp.lpSum([visit_vars[pi][pk] for pi in pois]) <= 1, 'Enter_' + pk + '_AtMostOnce'
        pb += pulp.lpSum([visit_vars[pk][pj] for pj in pois if pj != p0]) + isend_vars[pk] <= 1, \
              'Leave_' + pk + '_AtMostOnce'
    for pi in [x for x in pois if x != p0]:
        for pj in [y for y in pois if y != p0]:
            pb += dummy_vars[pi] - dummy_vars[pj] + 1 <= (M - 1) * (1 - visit_vars[pi][pj]), \
                  'SubTourElimination_' + pi + '_' + pj
    #pb.writeLP("traj_tmp.lp")
    
    # solve problem: solver should be available in PATH
    if USE_GUROBI == True:
        gurobi_options = [('TimeLimit', '7200'), ('Threads', str(N_JOBS)), ('NodefileStart', '0.2'), ('Cuts', '2')]
        pb.solve(pulp.GUROBI_CMD(path='gurobi_cl', options=gurobi_options)) # GUROBI
    else:
        pb.solve(pulp.COIN_CMD(path='cbc', options=['-threads', str(N_JOBS), '-strategy', '1', '-maxIt', '2000000']))#CBC
    visit_mat = pd.DataFrame(data=np.zeros((len(pois), len(pois)), dtype=np.float), index=pois, columns=pois)
    isend_vec = pd.Series(data=np.zeros(len(pois), dtype=np.float), index=pois)
    for pi in pois:
        isend_vec.loc[pi] = isend_vars[pi].varValue
        for pj in pois: visit_mat.loc[pi, pj] = visit_vars[pi][pj].varValue

    # build the recommended trajectory
    recseq = [p0]
    while True:
        pi = recseq[-1]
        pj = visit_mat.loc[pi].idxmax()
        value = visit_mat.loc[pi, pj]
        assert(int(round(value)) == 1)
        recseq.append(pj)
        if len(recseq) == L: 
            assert(int(round(isend_vec[pj])) == 1)
            return np.asarray([int(x) for x in recseq])