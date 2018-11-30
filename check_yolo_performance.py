# -*- coding: utf-8 -*-
"""
Created on Thu Jul 12 14:52:06 2018

given the benchmark annotation, compare the result of yolo with it, return 
TP/FP/TN/FN, as well as percision and recall.


@author: Wen Wen
"""

import argparse
import cv2
import os
import time
import numpy as np
import json

import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import matplotlib.pyplot as plt

def getIoU(bbx_benchmark,bbx_detect):
    """
    calculate Intersection over Union of two bounding boxes
    return 0 if no intersection
    
    """
    
    # get the cordinates of intersecting square
    x_inter_1=max(bbx_benchmark['x'],bbx_detect['x'])
    y_inter_1=max(bbx_benchmark['y'],bbx_detect['y'])
    x_inter_2=min(bbx_benchmark['x']+bbx_benchmark['width'],bbx_detect['x']+bbx_detect['width'])
    y_inter_2=min(bbx_benchmark['y']+bbx_benchmark['height'],bbx_detect['y']+bbx_detect['height'])
    
    # get intersect area
    inter_area = max(0, x_inter_2 - x_inter_1) * max(0, y_inter_2 - y_inter_1)
    
    # get bbx area
    benchmark_area = bbx_benchmark['width'] * bbx_benchmark['height']
    detect_area=bbx_detect['width'] * bbx_detect['height']
    
    # calculate IoU
    iou = inter_area / float(benchmark_area + detect_area - inter_area)
    
    # for debugging, check the result
    '''
    print('benchmark:(x1,y1)=',bbx_benchmark['x'],bbx_benchmark['y'],' (x2,y2)=',bbx_benchmark['x']+bbx_benchmark['width'],bbx_benchmark['y']+bbx_benchmark['height'])
    print('detect:(x1,y1)=',bbx_detect['x'],bbx_detect['y'],'(x2,y2)=',bbx_detect['x']+bbx_detect['width'],bbx_detect['y']+bbx_detect['height'])
    print('intersection area:',inter_area)
    print('benchmark area:',benchmark_area)
    print('detect area:',detect_area)
    print('IoU=',iou,'\n')
    '''
    
    
    return iou

def checkSingleImage(imgname,annos_benchmark,annos_detect,totalperformance,IOUthresh):
    # check every detected bbx, add the result to currentperformance
    performance=totalperformance
    
    # remove all the null object (none-car objects)
    annos_detect=[i for i in annos_detect if i['label']!='null']
    
    # special case 1: no detected, but benchmark has cars, all false negative
    if len(annos_detect)==0:
        if len(annos_benchmark)!=0:
            for bbx in annos_benchmark:
                if bbx['category'].lower()=='leading':
                    performance['leading']['fn']+=1
                    performance['overall']['fn']+=1
                else:
                    # no benchmark for leading car, tn
                    performance['overall']['fn']+=1
                    
    # special case 2: no benchmark, but detected, all false positive
    elif len(annos_benchmark)==0:
        if len(annos_detect)!=0:
            for bbx in annos_detect:
                if bbx['category'].lower()=='leading':
                    performance['leading']['fp']+=1
                    performance['overall']['fp']+=1
                else:
                    # no detection for leading car, tn
                    performance['overall']['fp']+=1
        
    # common case: both benchmark and detected file has bbx, calculate IoU
    else:
        benchlist=[] # to store the matched bbx
        detectlist=[] # to store the matched bbx
        for i in range(len(annos_benchmark)):
            # calculate IoU bbx in detect and bbx in benchmark            
            for j in range(len(annos_detect)):
                iou=getIoU(annos_benchmark[i],annos_detect[j])
                # true positive
                if iou>=IOUthresh:
                    if annos_benchmark[i]['category'].lower()==annos_detect[j]['category'].lower():
                        performance['overall']['tp']+=1 # tn for leading
                        if annos_detect[j]['category'].lower()=='leading':
                            performance['leading']['tp']+=1
                        
                    else:
                        # tp for overall
                        performance['overall']['tp']+=1
                        if annos_detect[j]['category'].lower()=='leading': 
                            # fp for leading car
                            performance['leading']['fp']+=1
                        else:
                            # fn for leading car
                            performance['leading']['fn']+=1
                    
                    # mark the matched bbx in benchmark
                    benchlist.append(i)  
                    detectlist.append(j)
                    # go to next benchmark if already have one match
        '''
        print('imgname',imgname)
        print('bench',benchlist,'bench len',len(annos_benchmark))
        print('detect',detectlist,'detect len',len(annos_detect),'\n')
        '''
        
        # find the unmatched in benchmark, fn
        for i in range(len(annos_benchmark)):
            # if matched, skip
            if i in benchlist:
                continue
            else:
                performance['overall']['fn']+=1
                if annos_benchmark[i]['category']=='leading':
                    # miss a leading car in detection
                    performance['leading']['fn']+=1
        
        # find the unmatched in detect, fp
        for i in range(len(annos_detect)):
            # if matched, skip
            if i in detectlist:
                continue
            else:
                performance['overall']['fp']+=1
                if annos_detect[i]['category']=='leading':
                    # miss a leading car in detection
                    performance['leading']['fp']+=1
                
    
    return performance

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', type=str, 
                        default='D:/Private Manager/Personal File/uOttawa/Lab works/2018 fall/BerkleyDeepDrive/bdd100k/detection results/Faster-RCNN inception ResNet/', 
                        help="File path of input data")
    parser.add_argument('--model_name',type=str,default='Faster-RCNN Inception ResNet',
                        help='model name for charts')
    parser.add_argument('--detected_path',type=str, 
                        default='D:/Private Manager/Personal File/uOttawa/Lab works/2018 fall/BerkleyDeepDrive/bdd100k/detection results/Faster-RCNN inception ResNet/annotation_val_detection.json',
                        help='path of detected result, if "none", search the annotation files under file_path')
    parser.add_argument('--benchmark_path',type=str, 
                        default='D:/Private Manager/Personal File/uOttawa/Lab works/2018 fall/BerkleyDeepDrive/bdd100k/labels/bdd100k_labels_images_val_VIVA_format.json',
                        help='path of benchmark path, if "none", search the annotation files under file_path')
    
    
    args = parser.parse_args()
    
    filepath=args.file_path
    folderdict=os.listdir(filepath)
    modelname=args.model_name
    detectpath=args.detected_path
    benchmarkpath=args.benchmark_path
    totalperformance={}
    threshlist=[0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,
                0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,0.999]
    precision_overall_list=[]
    precision_leading_list=[]
    recall_overall_list=[]
    recall_leading_list=[]
    MRs_overall_list=[]
    MRs_leading_list=[]
    # change IoU threshold from 0 to 1.0, interval 0.05
    for IOUthresh in threshlist:
    
        # initial the numbers for performance
        totalperformance[IOUthresh]={'leading':{'tp':0, 'fp':0, 'tn':0, 'fn':0},
                                            'overall':{'tp':0, 'fp':0, 'tn':0, 'fn':0}}
    
        if detectpath=='none' and benchmarkpath=='none':
            for foldername in folderdict:
                jsonpath=os.path.join(filepath,foldername)
                # load the json files
                if not os.path.exists(os.path.join(jsonpath,'annotationfull_'+foldername+'.json')):
                    continue   
                else:
                    benchmark=json.load(open(os.path.join(jsonpath,'annotationfull_'+foldername+'.json')))
                    detected=json.load(open(os.path.join(jsonpath,'annotation_'+foldername+'_'+modelname+'.json')))
            
                for imgname in detected:
                    # if not detected
                    if len(detected[imgname])==0:
                        annos_detect={}
                    else:
                        annos_detect=detected[imgname]['annotations']
                
                    # if no such a benchmark
                    if benchmark.get(imgname.split('_')[-1])==None:
                        annos_benchmark={}
                    else:
                        annos_benchmark=benchmark[imgname.split('_')[-1]]['annotations']
                
                    # calculate performance
                    totalperformance[IOUthresh]=checkSingleImage(imgname,annos_benchmark,annos_detect,totalperformance[IOUthresh],IOUthresh)
        else:# detection result and benchmark pathes are specified
            benchmark=json.load(open(benchmarkpath))
            detected=json.load(open(detectpath))
            
            for imgname in detected:
                # if not detected
                if len(detected[imgname])==0:
                    annos_detect={}
                else:
                    annos_detect=detected[imgname]['annotations']
            
                # if no such a benchmark
                if benchmark.get(imgname.split('_')[-1])==None:
                    annos_benchmark={}
                else:
                    annos_benchmark=benchmark[imgname.split('_')[-1]]['annotations']
            
                # calculate performance
                totalperformance[IOUthresh]=checkSingleImage(imgname,annos_benchmark,annos_detect,totalperformance[IOUthresh],IOUthresh)
        
        # calculate precision, recall and missrate
        precision_leading=totalperformance[IOUthresh]['leading']['tp']/(totalperformance[IOUthresh]['leading']['tp']+totalperformance[IOUthresh]['leading']['fp'])
        precision_overall=totalperformance[IOUthresh]['overall']['tp']/(totalperformance[IOUthresh]['overall']['tp']+totalperformance[IOUthresh]['overall']['fp'])
        precision_leading_list.append(precision_leading)
        precision_overall_list.append(precision_overall)        
        
        if totalperformance[IOUthresh]['leading']['tp']+totalperformance[IOUthresh]['leading']['fn']==0:
            print('tp+fn=0, no leading label in benchmark')
            recall_leading=0
        else:
            recall_leading=totalperformance[IOUthresh]['leading']['tp']/(totalperformance[IOUthresh]['leading']['tp']+totalperformance[IOUthresh]['leading']['fn'])
        recall_leading_list.append(recall_leading)
        
        recall_overall=totalperformance[IOUthresh]['overall']['tp']/(totalperformance[IOUthresh]['overall']['tp']+totalperformance[IOUthresh]['overall']['fn'])
        recall_overall_list.append(recall_overall)
        
        # save all precision and recall
        totalperformance[IOUthresh]['leading']['precision']=precision_leading
        totalperformance[IOUthresh]['overall']['precision']=precision_overall
        totalperformance[IOUthresh]['leading']['recall']=recall_leading
        totalperformance[IOUthresh]['overall']['recall']=recall_overall
        
        '''
        print('IoU threshold:',IOUthresh,'\n')
    
        print('overall performance on detecting cars:')
        print(totalperformance[IOUthresh]['overall'])
        print('precision:',precision_overall)
        print('recall:',recall_overall)
    
        print('performance on detecting leading cars:')
        print(totalperformance[IOUthresh]['leading'])
        print('precision:',precision_leading)
        print('recall:',recall_leading)
        '''
    
    # save the performance into json file
    with open(os.path.join(filepath,'performance.json'),'w') as savefile:
        savefile.write(json.dumps(totalperformance, sort_keys = True, indent = 4))
    
    
    # plot the precision, recall and MRs over all the cars and leading cars
    
    partname=filepath.split('/')[-1]
    
    chartaxis = [0.0,1.0,0.0,1.0]
    
    plt.axis(chartaxis)
    plt.plot(threshlist,precision_leading_list,'b.-',label='Leading')
    plt.plot(threshlist,precision_overall_list,'r.-',label='Overall')
    plt.title(modelname+' '+partname+' precision')
    plt.xlabel('IoU threshold')
    plt.legend(loc=1)
    plt.savefig(os.path.join(filepath,'precision.png'))
    plt.show()
    
    plt.axis(chartaxis)
    plt.plot(threshlist,recall_leading_list,'bs-', label='Leading')
    plt.plot(threshlist,recall_overall_list,'rs-',label='Overall')
    plt.title(modelname+' '+partname+' recall')
    plt.xlabel('IoU threshold')
    plt.legend(loc=1)
    plt.savefig(os.path.join(filepath,'recall.png'))
    plt.show()

    
    
    
""" End of file """