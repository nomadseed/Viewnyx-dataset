# -*- coding: utf-8 -*-
"""
Created on Wed Aug  1 13:36:25 2018

create TFrecord file of Viewnyx dataset
converting all the json benchmark into a single record file

args:
    file_path: image path, each time specify a folder corresponding with the 
        annotation,also the path to save the tfrecord file
    folder_number: how many folders do you want to process
    json_label: specify the json file with some label in their name

Example usage:
    python create_viewnyx_tf_record.py 
    --file_path ./your/own/path
    --tfrecord_name train.record
    

@author: Wen Wen
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import os
import argparse

import tensorflow as tf

from object_detection.utils import dataset_util


def GetClassID(class_label):
    """
    given class name, get the class id (int format)
    change this function if needed for multi-class object detection
    NEVER use index number 0, for tensorflow use 0 as a placeholder
    
    """
    if class_label.lower() == 'car':
        return 1
    else:
        return None


def CreateTFExample(img_path,img_name,annotation):
    """
    create tf record example
    this function runs once per image
    
    args:
        img_path: image path
        img_name: image name
        annotation: annotation dictionary for current image
    """
    #img_name=annotation['name'] # for viewnyx part 2
    
    
    with tf.gfile.GFile(os.path.join(img_path, img_name), 'rb') as fid:
        encoded_jpg = fid.read()
    
    img_format=img_name.split('.')[-1]
    width=annotation['width']
    height=annotation['height']
    
    xmins = []
    xmaxs = []
    ymins = []
    ymaxs = []
    classes_text = []
    classes = []
    
    for bbx in annotation['annotations']:
        xmins.append(bbx['x'] / width)
        xmaxs.append((bbx['x']+bbx['width']) / width)
        ymins.append(bbx['y'] / height)
        ymaxs.append((bbx['y']+bbx['height']) / height)
        classes_text.append(bbx['label'].lower().encode('utf8'))
        classes.append(GetClassID(bbx['label'].lower()))
    
    
    tf_example = tf.train.Example(features=tf.train.Features(feature={
        'image/height': dataset_util.int64_feature(height),
        'image/width': dataset_util.int64_feature(width),
        'image/filename': dataset_util.bytes_feature(img_name.encode('utf8')),
        'image/source_id': dataset_util.bytes_feature(img_name.encode('utf8')),
        'image/encoded': dataset_util.bytes_feature(encoded_jpg),
        'image/format': dataset_util.bytes_feature(img_format.encode('utf8')),
        'image/object/bbox/xmin': dataset_util.float_list_feature(xmins),
        'image/object/bbox/xmax': dataset_util.float_list_feature(xmaxs),
        'image/object/bbox/ymin': dataset_util.float_list_feature(ymins),
        'image/object/bbox/ymax': dataset_util.float_list_feature(ymaxs),
        'image/object/class/text': dataset_util.bytes_list_feature(classes_text),
        'image/object/class/label': dataset_util.int64_list_feature(classes),
    }))
    return tf_example
    

#def main(_):
if __name__ == '__main__':
    # pass the parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', type=str, 
                        default='testframes', 
                        help="select the file path for image folders")
    parser.add_argument('--tfrecord_name', type=str, 
                        default='train.record', 
                        help="select the file path for image folders")
    parser.add_argument('--folder_number',type=int, default=2,
                        help='set how many folders will be processed')
    parser.add_argument('--json_label',type=str, default='full',
                        help='use part of the name to specify the json file to be processed')
    
    args = parser.parse_args()
    filepath=args.file_path
    tfrecordname=args.tfrecord_name
    folderdict=os.listdir(filepath)
    jsonlabel=args.json_label
    foldernumber=args.folder_number
    foldercount=0
    
    for folder in folderdict:
        # skip the files, choose folders only
        if '.' in folder:
            continue 
        
        # for debug only, set the number of folders to be processed
        if foldercount>=foldernumber:
            break
        else:
            foldercount+=1
            
        imagepath=os.path.join(filepath,folder)
        filedict=os.listdir(imagepath)
        
        # announce the writer for tfrecord file, it will keep writing until closed
        writer = tf.python_io.TFRecordWriter(os.path.join(imagepath,tfrecordname))
        
        for jsonname in filedict:
            if 'json' in jsonname and jsonlabel in jsonname:
                annotations=json.load(open(os.path.join(imagepath,jsonname)))
                
                for i in annotations:
                    # specify the image name
                    #img_name=imagepath.split('\\')[-1]+'_'+annotations[i]['name'] # for viewnyx part1
                    img_name=annotations[i]['name'] # for viewnyx part 2
                    
                    tf_example=CreateTFExample(imagepath,img_name,annotations[i])
                    
                    writer.write(tf_example.SerializeToString())
        
        # indented samely as announcing the tfrecord
        writer.close()
                
        
        print('Successfully created the TFRecords: {}'.format(os.path.join(imagepath,tfrecordname)))
                    
    
'''
if __name__ == '__main__':
    tf.app.run()
'''








