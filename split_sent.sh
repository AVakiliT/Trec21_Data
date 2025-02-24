#!/bin/bash
#SBATCH--time=0:30:0
#SBATCH --nodes=1
#SBATCH --account=rrg-smucker
#SBATCH--mem=120G
#SBATCH --ntasks-per-node=1
#SBATCH--cpus-per-task=28

module load spark scipy-stack; export PYSPARK_DRIVER_PYTHON=ipython;export _JAVA_OPTIONS="-Xms256m -Xmx120G";source ~/avakilit/SPARKENV/bin/activate

spark-submit split_sent.py Top1kBM25 Top1kBM25_2021
