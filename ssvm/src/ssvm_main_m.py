import sys, os, pickle
import numpy as np
import random
import cvxopt

if len(sys.argv) != 4:
    print('Usage: python', sys.argv[0], 'WORK_DIR DATA_INDEX QUERY_INDEX')
    sys.exit(0)
else:
    work_dir = sys.argv[1]
    dat_ix = int(sys.argv[2])
    qix = int(sys.argv[3])

data_dir = os.path.join(work_dir, 'data')
src_dir = os.path.join(work_dir, 'src')
sys.path.append(src_dir)

from shared import TrajData, evaluate
from ssvm import SSVM
#import pyximport
#pyximport.install(setup_args={'include_dirs': np.get_include()}, reload_support=True)
from inference_lv import do_inference_list_viterbi

random.seed(1234554321)
np.random.seed(123456789)
cvxopt.base.setseed(123456789)

dat_obj = TrajData(dat_ix, data_dir=data_dir)

N_JOBS = 4         # number of parallel jobs
C_SET = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000, 3000]  # regularisation parameter
MC_PORTION = 0.1   # the portion of data that sampled by Monte-Carlo cross-validation
MC_NITER = 5       # number of iterations for Monte-Carlo cross-validation
SSVM_SHARE_PARAMS = True  # share params among POIs/transitions in SSVM
SSVM_MULTI_LABEL = True  # use multi-label SSVM
SSVM_VARIANT = 'D'

inference_method = do_inference_list_viterbi
bestC = pickle.load(open(os.path.join(data_dir, 'bestC-' + SSVM_VARIANT + '-' + dat_obj.dat_suffix[dat_ix] + '.pkl'), 'rb'))

recdict_ssvm = dict()
keys = sorted(dat_obj.TRAJID_GROUP_DICT.keys())

i = qix
ps, L = keys[i]
keys_cv = keys[:i] + keys[i+1:]

if (ps, L) not in bestC:
    sys.stderr.write('start POI of query %s does not exist in training set.\n' % str(keys[i]))
    sys.exit(0)

# use all training+validation set to compute POI features, 
# make sure features do NOT change for training and validation
trajid_set_i = set(dat_obj.trajid_set_all) - dat_obj.TRAJID_GROUP_DICT[keys[i]]
poi_info_i = dat_obj.calc_poi_info(list(trajid_set_i))
poi_set_i = {p for tid in trajid_set_i for p in dat_obj.traj_dict[tid] if len(dat_obj.traj_dict[tid]) >= 2}
if ps not in poi_set_i: 
    sys.stderr.write('start POI of query %s does not exist in training set.\n' % str(keys[i]))
    sys.exit(0)

best_C = bestC[(ps, L)]
print('\n--------------- Query: (%d, %d), Best_C: %f ---------------\n' % (ps, L, best_C))

# train model using all examples in training set and measure performance on test set
ssvm = SSVM(inference_train=inference_method, inference_pred=inference_method, dat_obj=dat_obj, 
            share_params=SSVM_SHARE_PARAMS, multi_label=SSVM_MULTI_LABEL, C=best_C, poi_info=poi_info_i)
if ssvm.train(sorted(trajid_set_i), n_jobs=N_JOBS) == True:
    y_hat_list = ssvm.predict(ps, L)
    print(y_hat_list)
    if y_hat_list is not None:
        recdict_ssvm[(ps, L)] = {'PRED': y_hat_list, 'W': ssvm.osssvm.w, 'C': ssvm.C}

fssvm = os.path.join(data_dir, 'ssvm-' + SSVM_VARIANT + '-' + dat_obj.dat_suffix[dat_ix] + '-%d.pkl' % (qix))
pickle.dump(recdict_ssvm, open(fssvm, 'bw'))

