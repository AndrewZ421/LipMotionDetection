##############################################################
### Copyright (c) 2018-present, Xuanyi Dong                ###
### Style Aggregated Network for Facial Landmark Detection ###
### Computer Vision and Pattern Recognition, 2018          ###
##############################################################
import sqlite3
import os, math
import os.path as osp
import copy
import numpy as np
import init_path
from scipy.io import loadmat
import datasets

#Change this paths according to your directories
this_dir = osp.dirname(os.path.abspath(__file__))
SAVE_DIR = osp.join(this_dir, 'lists', 'AFLW')
higher_dir = osp.abspath(osp.join(this_dir, '..'))
print(higher_dir)
if not osp.isdir(SAVE_DIR): os.makedirs(SAVE_DIR)
image_dir = osp.join(higher_dir, 'datasets', 'AFLW-Style')
annot_dir = osp.join(higher_dir, 'datasets', 'AFLW-Style', 'annotation')
print ('data dir : {}'.format(image_dir))
print ('annotation dir : {}'.format(annot_dir))


class AFLWFace():
  def __init__(self, index, name, mask, landmark, box):
    self.image_path = name
    self.face_id = index
    self.face_box = [float(box[0]), float(box[2]), float(box[1]), float(box[3])]
    mask = np.expand_dims(mask, axis=1)
    landmark = landmark.copy()
    self.landmarks = np.concatenate((landmark, mask), axis=1)

  def get_face_size(self, use_box):
    box = []
    if use_box == 'GTL':
      box = datasets.dataset_utils.PTSconvert2box(self.landmarks.copy().T)
    elif use_box == 'GTB':
      box = [self.face_box[0], self.face_box[1], self.face_box[2], self.face_box[3]]
    else:
      assert False, 'The box indicator not find : {}'.format(use_box)
    assert box[2] > box[0], 'The size of box is not right [{}] : {}'.format(self.face_id, box)
    assert box[3] > box[1], 'The size of box is not right [{}] : {}'.format(self.face_id, box)
    face_size = math.sqrt( float(box[3]-box[1]) * float(box[2]-box[0]) )
    box_str = '{:.2f} {:.2f} {:.2f} {:.2f}'.format(box[0], box[1], box[2], box[3])
    return box_str, face_size

  def check_front(self):
    oks = 0
    box = self.face_box
    for idx in range(self.landmarks.shape[0]):
      if bool(self.landmarks[idx,2]):
        x, y = self.landmarks[idx,0], self.landmarks[idx,1]
        if x > self.face_box[0] and x < self.face_box[2]:
          if y > self.face_box[1] and y < self.face_box[3]:
            oks = oks + 1
    return oks == 19
    
  def __repr__(self):
    return ('{name}(path={image_path}, face-id={face_id})'.format(name=self.__class__.__name__, **self.__dict__))


def save_to_list_file(allfaces, lst_file, image_style_dir, annotation_dir, face_indexes, use_front, use_box):
  save_faces = []
  for index in face_indexes:
    face = allfaces[index]
    if use_front == False or face.check_front():
      save_faces.append( face )
  print ('Prepare to save {} face images into {}'.format(len(save_faces), lst_file))

  lst_file = open(lst_file, 'w')
  all_face_sizes = []
  for face in save_faces:
    image_path = face.image_path
    sub_dir, base_name = image_path.split('/')
    cannot_dir = osp.join(annotation_dir, sub_dir)
    cannot_path = osp.join(cannot_dir, base_name.split('.')[0] + '-{}.pts'.format(face.face_id))
    if not osp.isdir(cannot_dir): os.makedirs(cannot_dir)
    image_path = osp.join(image_style_dir, image_path)
    assert osp.isfile(image_path), 'The image [{}/{}] {} does not exsit'.format(index, len(save_faces), image_path)

    pts_str = datasets.PTSconvert2str( face.landmarks.T )
    pts_file = open(cannot_path, 'w')
    pts_file.write('{}'.format(pts_str))
    pts_file.close()

    box_str, face_size = face.get_face_size(use_box)

    lst_file.write('{} {} {} {}\n'.format(image_path, cannot_path, box_str, face_size))
    all_face_sizes.append( face_size )
  lst_file.close()

  all_faces = np.array( all_face_sizes )
  print ('all faces : mean={}, std={}'.format(all_faces.mean(), all_faces.std()))

if __name__ == "__main__":
  mat_path = osp.join(this_dir, 'AFLWinfo_release.mat')
  aflwinfo = dict()
  mat = loadmat(mat_path)
  total_image = 24386
  # load train/test splits
  ra = np.squeeze(mat['ra']-1).tolist()
  aflwinfo['train-index'] = ra[:20000]
  aflwinfo['test-index'] = ra[20000:]
  aflwinfo['name-list'] = []
  # load name-list
  for i in range(total_image):
    name = mat['nameList'][i,0][0]
    name = name[:-4] + '.jpg'
    aflwinfo['name-list'].append( name )
  aflwinfo['mask'] = mat['mask_new'].copy()
  aflwinfo['landmark'] = mat['data'].reshape((total_image, 2, 19))
  aflwinfo['landmark'] = np.transpose(aflwinfo['landmark'], (0,2,1))
  aflwinfo['box'] = mat['bbox'].copy()
  allfaces = []
  for i in range(total_image):
    face = AFLWFace(i, aflwinfo['name-list'][i], aflwinfo['mask'][i], aflwinfo['landmark'][i], aflwinfo['box'][i])
    allfaces.append( face )
  
  USE_BOXES = ['GTL', 'GTB']
  STYLES = ['Original', 'Gray', 'Sketch', 'Light']
  for STYLE in STYLES:
    temp_dir = osp.join(SAVE_DIR, STYLE)
    if not osp.isdir(temp_dir): os.makedirs(temp_dir)
    for USE_BOX in USE_BOXES:
      save_to_list_file(allfaces, osp.join(SAVE_DIR, STYLE, 'train.{}'.format(USE_BOX)),      osp.join(image_dir, 'aflw-'+STYLE), annot_dir, aflwinfo['train-index'], False, USE_BOX)
      save_to_list_file(allfaces, osp.join(SAVE_DIR, STYLE, 'test.{}'.format(USE_BOX)),       osp.join(image_dir, 'aflw-'+STYLE), annot_dir, aflwinfo['test-index'], False, USE_BOX)
      save_to_list_file(allfaces, osp.join(SAVE_DIR, STYLE, 'test.front.{}'.format(USE_BOX)), osp.join(image_dir, 'aflw-'+STYLE), annot_dir, aflwinfo['test-index'], True, USE_BOX)
      save_to_list_file(allfaces, osp.join(SAVE_DIR, STYLE, 'all.{}'.format(USE_BOX)),        osp.join(image_dir, 'aflw-'+STYLE), annot_dir, aflwinfo['train-index'] + aflwinfo['test-index'], False, USE_BOX)
