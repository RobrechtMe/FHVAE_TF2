from __future__ import absolute_import
import os
import sys
print(sys.path)
print(os.getcwd())
sys.path.insert(0, os.getcwd())
import time
import argparse
import shutil
import pickle
import ast
import tensorflow as tf
##
gpus = tf.config.experimental.list_physical_devices('GPU')
# for gpu in gpus
if gpus:
    gpu = gpus[0]
    try:
        tf.config.experimental.set_visible_devices(gpu, 'GPU')
        tf.config.experimental.set_memory_growth(gpu, enable=True)
        # break
    except RuntimeError as e:
        print(e)
        pass
##
from configparser import ConfigParser
from collections import OrderedDict
from scripts.test.eval_loaders import load_data_reg
from fhvae.runners.test_fhvae import test_reg
from fhvae.models.reg_fhvae_lstm import RegFHVAEnew
from fhvae.models.reg_fhvae_transf import RegFHVAEtransf

# os.environ["CUDA_VISIBLE_DEVICES"]="0"

'''
Commands
Script path:
/users/spraak/jponcele/JakobFHVAE/scripts/test/run_eval.py

Parameters:
--expdir /esat/spchdisk/scratch/jponcele/fhvae_jakob/exp
Working directory:
/users/spraak/jponcele/JakobFHVAE
'''


def main(conf, dump_only=True):
    ''' main function '''
    print('Using split: %s' % conf['set_name'])
    expdir = conf['expdir']
    os.makedirs(os.path.join(expdir, conf['set_name']), exist_ok=True)
    # read and copy the config file, change location if necessary
    # shutil.copyfile('./config.cfg', os.path.join(expdir, 'test', 'config.cfg'))


    # load tr_shape and classes from training stage
    with open(os.path.join(expdir, "trainconf.pkl"), "rb") as fid:
        trainconf = pickle.load(fid)
    conf['tr_shape'] = trainconf['tr_shape']
    conf['lab2idx'] = trainconf['lab2idx']
    conf['train_talab_vals'] = trainconf['talab_vals']

    # lower the batch size when you have memory problems!
    print('Loading data into memory...')
    tt_iterator, tt_iterator_by_seqs, tt_seqs, tt_dset = \
        load_data_reg(conf['dataset_test'], conf['set_name'], conf['fac_root'], conf['facs'], conf['talabs'], conf['train_talab_vals'])

    # identify regularizing factors
    used_labs = conf['facs'].split(':')

    # When testing on new dataset, set this to HACK  (EXPERIMENTAL, NOT TESTED !!)
    if conf['dataset_test'] == conf['dataset']:
        c_n = trainconf['c_n']
        b_n = trainconf['b_n']
    else:
        print("Testing on different dataset then trained on, set number of classes manually.")
        c_n = OrderedDict([(used_labs[0], 3), (used_labs[1], 9)])  # HACK
        b_n = c_n

    conf['b_n'] = b_n
    conf['c_n'] = c_n

    # if we did not use the hierarchical sampling during training, the mu2table will be larger than nmu2 in the config
    if 'nmu2' in trainconf:
        conf['nmu2'] = trainconf['nmu2']

    # initialize the model
    if conf['model'] == 'LSTM':
        model = RegFHVAEnew(z1_dim=conf['z1_dim'], z2_dim=conf['z2_dim'], z1_rhus=conf['z1_rhus'], z2_rhus=conf['z2_rhus'], \
                            x_rhus=conf['x_rhus'], nmu2=conf['nmu2'], z1_nlabs=b_n, z2_nlabs=c_n, \
                            mu_nl=None, logvar_nl=None, tr_shape=conf['tr_shape'], bs=conf['batch_size'], \
                            alpha_dis=conf['alpha_dis'], alpha_reg_b=conf['alpha_reg_b'], alpha_reg_c=conf['alpha_reg_c'])

    if conf['model'] == 'transformer':
        model = RegFHVAEtransf(z1_dim=conf['z1_dim'], z2_dim=conf['z2_dim'], nmu2=conf['nmu2'], x_rhus=conf['x_rhus'], \
                            tr_shape=conf['tr_shape'], z1_nlabs=b_n, z2_nlabs=c_n, mu_nl=None, logvar_nl=None, \
                            d_model=conf['d_model'], num_enc_layers=conf['num_enc_layers'], num_heads=conf['num_heads'], \
                            dff=conf['dff'], pe_max_len=conf['pe_max_len'], rate=conf['rate'], \
                            alpha_dis=conf['alpha_dis'], alpha_reg_b=conf['alpha_reg_b'], alpha_reg_c=conf['alpha_reg_c'])

    #START
    test_reg(expdir, model, conf, tt_iterator, tt_iterator_by_seqs, tt_seqs, tt_dset, dump_only)


def load_config(conf):
    ''' Load configfile and extract arguments as a dict '''
    cfgfile = ConfigParser(interpolation=None)
    cfgfile.read(conf)
    test_conf = dict(cfgfile.items('RegFHVAE'))
    for key, val in test_conf.items():
        try:
            # get numbers as int/float/list
            test_conf[key] = ast.literal_eval(val)
        except:
            # text / paths
            pass
    return test_conf


if __name__ == '__main__':

    print("I am process %s, running on %s: starting (%s)" % (
        os.getpid(), os.uname()[1], time.asctime()))

    #parse the arguments
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--expdir", type=str, default="./exp",
                        help="where to store the experiment (directory containing the trained model)")
    parser.add_argument("--config", type=str, default="./config.cfg",
                        help="configuration file to use for testing (default is the one stored in expdir)")
    parser.add_argument("--dump", action='store_true', help="dump all mu-values of dev, train, test sets (default: False)")
    args = parser.parse_args()

    if not os.path.isdir(args.expdir):
        print("Expdir does not exist.")
        exit(1)
    conf = load_config(os.path.join(args.expdir, 'config.cfg'))
    conf['expdir'] = args.expdir
    if args.dump:
        print('Dump mode on: dump all mu-values of dev, train, test sets')
        conf['set_name'] = 'test'
        main(conf, dump_only=False)
        for set_name in ['dev', 'train']:
            conf['set_name'] = set_name
            main(conf, dump_only=True)
    else:
        print('Dump mode off')
        main(conf, dump_only=False)
