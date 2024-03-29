# Skin surface extraction

This repository contains the code for a Slicer module that can be used to automatically extract the skin surface in various MR sequences (T1, post-contrast T1, T2, FLAIR).

This project was initiated during the [36th NA-MIC Project Week](https://projectweek.na-mic.org/PW36_2022_Virtual/Projects/SkinSegmentation/).

## Installation

## Requirements
You must install PyTorch before. The easiest way is to use the "PyTorch" module available in the "Extensions manager". 


### Option 1
Clone this repository:

```shell
git clone https://github.com/ReubenDo/SlicerSkinSegmentator.git
```

### Option 2

[Download the zipped directory](https://github.com/ReubenDo/SlicerSkinSegmentator/archive/refs/heads/main.zip) and unzip it.

### Add directory in Slicer

In Slicer, go to `Edit -> Application Settings -> Modules` and add the cloned/downloaded folder to the `Additional module paths`. When prompted, restart Slicer.

## Algorithm description

![Brain Skin Segmentator module](./screenshots/example.png)

TODO
