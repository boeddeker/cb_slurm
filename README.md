# My scripts for SLURM

The scripts are designed for Noctua2, but probably they will work on other clusters.

Special properties of Noctua2:
 - Privacy: Users cannot see Jobs of other users.
 - It is possible to submit jobs that confuse SLURM: A job can have 5 a100 on a node with 4 GPUs. gres_gpu:a100 is then wrong, while gres_gpu is correct.


My cmd to monitor all jobs: `vatch.py -c -n 180 "soverview.py; sacct.py $(date -d '45 hour ago' +%D-%R)"`
Monitoring a job output: `stail.py <jobid>` (Sometimes a bit buggy)

For debugging: `soverview_gpus.py`


```
$ mon/sacct.py $(date -d '1 hour ago' +%D-%R) --mine
========================================================================================================================================================================================================================
User |   JobID | Name                   | State            |             Elapsed |     Start |      End |   n | cpu |    gpu |    mem | CEff | MEff |  billing |  N | Partition | Acc | QoS  | Nodes                    
========================================================================================================================================================================================================================
cbj  | 4646900 | abcdefghijklmnopqrstuv | RUNNING          | 00:12:20 / 12:00:00 |     20:44 | [      ] | 200 | 200 |      - | 819.2G |    - |    - |  88, 426 | 11 |    normal | nt2 | cont | n2cn[0168-0169,0172,03...
========================================================================================================================================================================================================================
==============================================================
State    Partition  User  cpu  gpu     mem  billing  billing/h
==============================================================
RUNNING  gpu        cbj    16    2   82 GB      566         20
RUNNING  normal     cbj   200    0  819 GB       88        426
==============================================================
```

```
$ mon/soverview.py
===================================================================================================================================================
  N  Partition     state_flags        cpu/N    mem/N               cpu           mem / GB   gres_gpu  gres_gpu:a100  gres_fpga:u280  gres_fpga:520n
===================================================================================================================================================
 52  all,normal    RESERVED             128   240 GB      96 /   6_656      192 /  12_480          -              -               -               -
828  all,normal                         128   240 GB  95_785 / 105_984  170_943 / 198_720          -              -               -               -
 90  *             DRAIN                128   240 GB       2 /  11_520        4 /  21_600          -              -               -               -
 20  all,normal    RESERVED, PLANNED    128   240 GB       0 /   2_560        0 /   4_800          -              -               -               -
  1  all,dgx                            128   950 GB       0 /     128        0 /     950    0 /   8        0 /   8               -               -
  4  all,fpga      RESERVED             128   485 GB       0 /     512        0 /   1_940          -              -          0 / 12               -
 12  all,fpga                           128   485 GB       0 /   1_536        0 /   5_820          -              -          0 / 36               -
  3  all,fpga                           128   485 GB       0 /     384        0 /   1_455          -              -               -               -
 17  all,fpga                           128   485 GB       0 /   2_176        0 /   8_245          -              -               -          0 / 34
 31  all,gpu                            128   485 GB     198 /   3_968    7_036 /  15_035  111 / 124      111 / 124               -               -
  1  all,gpu       RESERVED             128   485 GB       0 /     128        0 /     485    2 /   4        2 /   4               -               -
  3  all,hacc                           128   485 GB     128 /     384      485 /   1_455          -              -               -               -
  5  all,hugemem                        128  1900 GB     512 /     640    7_200 /   9_500          -              -               -               -
 66  all,largemem                       128   950 GB   4_972 /   8_448   42_857 /  62_700          -              -               -               -
===================================================================================================================================================

```

```
$ mon/soverview_gpus.py
======================================================
name       comment  extra  state   state_flags  reason
======================================================
n2gpu1201                  mixed            []        

======================================================
===========================================================================================================================
cpu_load  free_memory  gres_drained   hostname                                                               tres_used/tres
===========================================================================================================================
421            459725           N/A  n2gpu1201  cpu:13/128,mem:308036M/485000M,billing:?/128,gres/gpu:4/4,gres/gpu:a100:4/4
===========================================================================================================================
```

```
$ mon/smaintenence.py
ReservationName=fpga_aurora StartTime=... EndTime=... Duration=...
   Nodes=... NodeCnt=1 CoreCnt=128 Features=(null) PartitionName=(null) Flags=...
   TRES=cpu=128
   Users=... Groups=(null) Accounts=(null) Licenses=(null) State=ACTIVE BurstBuffer=(null) Watts=n/a
   MaxStartDelay=(null)
```

