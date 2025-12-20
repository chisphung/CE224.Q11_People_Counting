
people_counting - v3 2025-10-20 11:55pm
==============================

This dataset was exported via roboflow.com on October 20, 2025 at 4:56 PM GMT

Roboflow is an end-to-end computer vision platform that helps you
* collaborate with your team on computer vision projects
* collect & organize images
* understand and search unstructured image data
* annotate, and create datasets
* export, train, and deploy computer vision models
* use active learning to improve your dataset over time

For state of the art Computer Vision training notebooks you can use with this dataset,
visit https://github.com/roboflow/notebooks

To find over 100k other datasets and pre-trained models, visit https://universe.roboflow.com

The dataset includes 1422 images.
People are annotated in YOLOv11 format.

The following pre-processing was applied to each image:

The following augmentation was applied to create 2 versions of each source image:

The following transformations were applied to the bounding boxes of each image:
* 50% probability of horizontal flip
* 50% probability of vertical flip
* Randomly crop between 0 and 20 percent of the bounding box
* Random brigthness adjustment of between -15 and +15 percent
* Random Gaussian blur of between 0 and 2.5 pixels
* Salt and pepper noise was applied to 0.1 percent of pixels


