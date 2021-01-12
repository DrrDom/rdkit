#!/usr/bin/env python3
# author          : Pavel Polishchuk
# license         : BSD-3
#==============================================================================

__author__ = 'Pavel Polishchuk'

import sys
import argparse
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors, QED
from rdkit.Chem.Scaffolds.MurckoScaffold import GetScaffoldForMol
from multiprocessing import Pool, cpu_count


descriptor_names = ['HBA', 'HBD', 'complexity', 'NumRings', 'RTB', 'TPSA', 'logP', 'MR', 'MW', 'Csp3', 'fmf', 'qed']


def calc(smi, name):
    m = Chem.MolFromSmiles(smi)
    if m is not None:
        hba = rdMolDescriptors.CalcNumHBA(m)
        hbd = rdMolDescriptors.CalcNumHBD(m)
        nrings = rdMolDescriptors.CalcNumRings(m)
        rtb = rdMolDescriptors.CalcNumRotatableBonds(m)
        psa = rdMolDescriptors.CalcTPSA(m)
        logp, mr = rdMolDescriptors.CalcCrippenDescriptors(m)
        mw = rdMolDescriptors._CalcMolWt(m)
        csp3 = rdMolDescriptors.CalcFractionCSP3(m)
        fmf = GetScaffoldForMol(m).GetNumHeavyAtoms() / m.GetNumHeavyAtoms()
        qed = QED.qed(m)
        return name, hba, hbd, hba + hbd, nrings, rtb, round(psa, 2), round(logp, 2), round(mr, 2), round(mw, 2), \
               round(csp3, 3), round(fmf, 3), round(qed, 3)
    else:
        sys.stderr.write('smiles %s cannot be parsed (%s)' % (smi, name))
        return None


def calc_mp(items):
    return calc(*items)


def read_smi(fname, sep, start_pos, nlines):
    start_pos -= 1
    if nlines is not None:
        end_pos = start_pos + nlines
    else:
        end_pos = float("inf")
    with open(fname) as f:
        for i, line in enumerate(f):
            if i >= start_pos:
                if i < end_pos:
                    items = line.strip().split(sep)
                    if len(items) == 1:
                        yield items[0], items[0]
                    else:
                        yield items[0], items[1]
                else:
                    raise StopIteration


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Calculation of physicochemical parameters with RDKit.')
    parser.add_argument('-i', '--in', metavar='input.smi', required=True,
                        help='input SMILES file. Should contain mol title as a second field.'
                             'Fields are tab-separated. No header.')
    parser.add_argument('-o', '--out', metavar='output.txt', required=True,
                        help='output text file with calculated physicochemical properties. '
                             'Molecules causing errors will be reported to stderr.')
    parser.add_argument('-s', '--sep', metavar='CHAR', required=False, default=None,
                        help='Field separator in input file. Default: whitespaces.')
    parser.add_argument('-p', '--startpos', metavar='NUMBER', required=False, default=0,
                        help='Starting line number to read SMILES. Default: 1 (beginning of the file).')
    parser.add_argument('-l', '--lines', metavar='NUMBER', required=False, default=None,
                        help='Number of lines (SMILES) to process. Default: None (all lines till the end of the file).')
    parser.add_argument('-c', '--ncpu', metavar='INTEGER', required=False, default=1,
                        help='Number of CPU cores to use. Default: 1.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='print progress to STDERR.')

    args = vars(parser.parse_args())
    for o, v in args.items():
        if o == "in": in_fname = v
        if o == "out": out_fname = v
        if o == "ncpu": ncpu = int(v)
        if o == "verbose": verbose = v
        if o == "sep": sep = v
        if o == "startpos": start_pos = int(v)
        if o == "lines": nlines = int(v) if v is not None else None

    p = Pool(min(ncpu, cpu_count()))

    with open(out_fname, 'wt') as f:
        f.write('\t'.join(['Name'] + descriptor_names) + '\n')
        for i, res in enumerate(p.imap(calc_mp, read_smi(in_fname, sep, start_pos, nlines), chunksize=100)):
            if res:
                f.write('\t'.join(map(str, res)) + '\n')
            if verbose and (i + 1) % 1000 == 0:
                sys.stderr.write('\r%i molecules passed' % (i + 1))
                sys.stderr.flush()
