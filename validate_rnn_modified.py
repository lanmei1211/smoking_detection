"""
Validate our RNN. Basically just runs a validation generator on
about the same number of videos as we have in our test set.
"""
import urllib

import cv2
from keras.callbacks import TensorBoard, ModelCheckpoint, CSVLogger
from tqdm import tqdm

from models import ResearchModels
import numpy as np
import operator
import random
import glob
import os.path
import os
from data_processor import DataSet
import sys
from processor import process_image
from keras.models import load_model
from matplotlib import pyplot as plt
import json
sys.path.insert(1, 'data')
from data.extract_files import extract_files
from extract_features_full import extract_full_features
from keras.utils.data_utils import get_file


def validate(data_type, model, seq_length=40, saved_model=None,
             class_limit=None, image_shape=None):
    batch_size = 32

    # Get the data and process it.
    if image_shape is None:
        data = DataSet(
            seq_length=seq_length,
            class_limit=class_limit
        )
    else:
        data = DataSet(
            seq_length=seq_length,
            class_limit=class_limit,
            image_shape=image_shape
        )

    val_generator = data.frame_generator(batch_size, 'test', data_type)

    # Get the model.
    rm = ResearchModels(len(data.classes), model, seq_length, saved_model)

    # Evaluate!
    results = rm.model.evaluate_generator(
        generator=val_generator,
        val_samples=3200)

    print(results)
    print(rm.model.metrics_names)


def main(videos=5):
    seq_length = 50
    # weights_path = get_file('lstm-features.hdf5', 'https://1drv.ms/u/s!AjwTYpyMoMlUll4oFEpdBU9dlppN?e=WVXhgu')
    # url = 'https://1drv.ms/u/s!AjwTYpyMoMlUll4oFEpdBU9dlppN?e=WVXhgu'
    # urllib.request.urlretrieve(url, 'data/checkpoints/lstm-features.hdf5')
    model = load_model('data/checkpoints/lstm-features.009-0.454.hdf5')
    # model = load_model('data/checkpoints/lstm-features.hdf5')

    extract_files(folders=['check'])
    extract_full_features(seq_length=seq_length)

    if model == 'conv_3d' or model == 'lrcn':
        data_type = 'images'
        image_shape = (80, 80, 3)
    else:
        data_type = 'features'
        image_shape = None

    # validate(data_type, model, saved_model=None,
    #          image_shape=image_shape, class_limit=4)

    output_json = {}
    output_json["smoking"] = []
    test_dir = "check"
    data = DataSet(seq_length=seq_length, check_dir='check')
    # model = load_model('data/checkpoints/inception.057-1.16.hdf5')
    for video in data.data:
        X, y = [], []

        sequences = data.get_extracted_sequence(data_type, video)
        total = sequences.shape[0]
        frames = np.arange(total)
        frame_pred = np.zeros(total)
        # print("Size : " + str(total))
        frame_pred_prob = []
        # X.append(sequence)
        y.append(data.get_class_one_hot(video[1]))
        print("video: " + video[2])
        end_frame = 50
        start_frame = 0
        # print("Number of frames: ", total )
        label_predictions = {}
        while end_frame <= sequences.shape[0]:

            X = []
            # print("video: " + video[2] + " start frame: " + str(start_frame) + " end frame: " + str(end_frame))
            X.append(sequences[start_frame: end_frame,:])
            # sequence = sequence.reshape(1, 3, 3)
            predictions = model.predict(np.array(X), batch_size=1)

            # Show how much we think it's each one.
            label_predictions = {}
            for i, label in enumerate(data.classes):
                # print(predictions)
                label_predictions[label] = predictions[0][i]
            # print(label_predictions)
            frame_pred_prob.append(str(label_predictions["smoking"]))
            if label_predictions["smoking"] > 0.5:
                frame_pred[start_frame:end_frame] = 1
            #
            # sorted_lps = sorted(label_predictions.items(), key=operator.itemgetter(1), reverse=True)
            # for i, class_prediction in enumerate(sorted_lps):
            #     # Just get the top five.
            #     # if i > 4:
            #     #     break
            #     print("%s: %.2f" % (class_prediction[0], class_prediction[1]))
            #     i += 1
            start_frame += 1
            end_frame += 1

        for i in range(start_frame, end_frame-1):
            frame_pred_prob.append(str(label_predictions["smoking"]))
            if label_predictions["smoking"] > 0.5:
                frame_pred[i] = 1
        # print(frame_pred)
        plt.title("Smoking action detection")
        plt.xlabel("Frame")
        plt.ylabel("Smoking action present")
        plt.plot(frames, frame_pred)

        output_path = os.path.join('data', 'out', video[2] + '.png')
        print("Saving output labels to: ", output_path)

        plt.savefig(output_path)
        plt.show()
        plt.figure()
        output_json["smoking"] = list(zip(frames.tolist(), frame_pred_prob))
        y = json.dumps(output_json)
        # with open('frameLabel.json', 'w') as outfile:
        #     json.dump(y, outfile)
        output_path = os.path.join('data','out',video[2] + '.json')
        print(y)
        with open(output_path, 'w') as outfile:
            json.dump(output_json, outfile)
            print('Output JSON saved under {}'.format(output_path))
        label_video(video, frame_pred, frame_pred_prob)

def label_video(video_path, labels, label_prob):
    print('Starting: {}'.format(video_path[2]))
    output_path = os.path.join('data', 'out')
    # Read and write

    start_frame = 0
    end_frame = None
    filepath = os.path.join('data', video_path[0], video_path[1], video_path[2] + "." + video_path[4])
    reader = cv2.VideoCapture(filepath)
    # video_fn = video + '.avi'
    video_fn = video_path[2]+'.avi'
    os.makedirs(output_path, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    fps = reader.get(cv2.CAP_PROP_FPS)
    num_frames = int(reader.get(cv2.CAP_PROP_FRAME_COUNT))
    writer = None
    # Text variables
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 2
    font_scale = 0.35
    print("Filepath : ", filepath)
    print("Total number of frames ", str(num_frames) )
    # Frame numbers and length of output video
    frame_num = 0
    assert start_frame < num_frames - 1
    end_frame = end_frame if end_frame else num_frames
    pbar = tqdm(total=end_frame-start_frame)

    while reader.isOpened():
        _, image = reader.read()
        if image is None:
            break
        frame_num += 1

        if frame_num < start_frame:
            continue
        pbar.update(1)

        # Image size
        height, width = image.shape[:2]

        # Init output writer
        if writer is None:
            writer = cv2.VideoWriter(os.path.join(output_path, video_fn), fourcc, fps,
                                     (height, width)[::-1])
        # print("frame num " + str(frame_num))
        label = 'smoking' if labels[frame_num-1] == 1 else 'non_smoking'
        color = (0, 255, 0) if labels[frame_num-1] == 0 else (0, 0, 255)
        # cv2.putText(image,  'Label =>' + str(label), (x, y + h + 30),
        #             font_face, font_scale,
        #             color, thickness, 2)
        cv2.putText(image, 'Frame num: ' + str(frame_num) + ', Label =>' + str(label) +
                    ', Prob =>' + label_prob[frame_num-1], (10, 20),
                    font_face, font_scale,
                    color, thickness, 2)
        # cv2.putText(image, 'Frame num: ' + str(frame_num) + ', Label =>' + str(label) +
        #             ', Prob =>' + label_prob[frame_num-1], (10, 20),
        #             font_face, font_scale,
        #             color, thickness, 2)
        if frame_num >= end_frame:
            break

        cv2.imshow('test', image)
        cv2.waitKey(1)     # About 30 fps
        writer.write(image)
    pbar.close()
    if writer is not None:
        writer.release()
        print('Finished! Output saved under {}'.format(output_path))
    else:
        print('Input video file was empty')

if __name__ == '__main__':
    main()
