#!/usr/bin/env bash
#SBATCH --account=rrg-smucker
#SBATCH --time=0-2:0:0
#SBATCH --array=34,13,31
# --array=1-51
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --gres=gpu:v100l:1
#SBATCH --output=slurm/%A_%a.out

#build environment
#virtualenv ~/PYGAGGLE
#source ~/PYGAGGLE/bin/activate
#module load rust
#module load swig
#pip install git+https://github.com/castorini/pygaggle.git
#','.join(map(str,set(range(101,151)).difference(set([int(re.search('topic-(.*).run', s).group(1)) for s in glob.glob("./output_Top1kBM25_mt5_2021_base-med/*")]))))


module load StdEnv  gcc  cuda/11 faiss arrow python java
source ~/PYGAGGLE/bin/activate
#pip install --upgrade pip

echo "Starting script..."

#~/PYGAGGLE/bin/python mdt5.py --topic_no $SLURM_ARRAY_TASK_ID \
# --topic_file /project/6004803/smucker/group-data/topics/misinfo-2021-topics.xml \
# --model_type base-med \
# --no-duo \
# --bm25run Top1kBM25_2021

~/PYGAGGLE/bin/python mdt5.py --topic_no $SLURM_ARRAY_TASK_ID \
 --topic_file /project/6004803/smucker/group-data/topics/2019topics.xml \
 --model_type base-med \
 --no-duo \
 --bm25run Top1kBM25_2019

#~/PYGAGGLE/bin/python mdt5.py --topic_no $SLURM_ARRAY_TASK_ID \
# --topic_file /project/6004803/smucker/group-data/topics/2019topics.xml \
# --model_type base \
# --bm25run /project/6004803/avakilit/Trec21_Data/Top1kBM25_2019_1p_passages/part-00000-a697cfb9-9405-449d-8548-e4ddc6ca9f7a-c000.snappy.parquet

