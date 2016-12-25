from keras.utils.visualize_util import plot
from keras.preprocessing.image import ImageDataGenerator
from keras import backend as K
import numpy as np
import h5py, pickle
from os.path import abspath, dirname
from os import listdir
import scipy as sp
from datetime import datetime
from shutil import copyfile
from PIL import Image, ImageEnhance, ImageFilter
from random import randint

ROOT = dirname(dirname(abspath(__file__)))
TEST_DIR = ROOT + '/test/'
channels, img_width, img_height = 3, 224, 224
mini_batch_sz = 8
ext = '.jpg'
lb, lbub, ublb, ub = 0.1, 0.4, 0.6, 0.9
zoom_width, zoom_height, step = 120, 120, 40

def logloss(actual, preds):
	epsilon = 1e-15
	ll = 0
	for act, pred in zip(actual, preds):
		pred = max(epsilon, pred)
		pred = min(1-epsilon, pred)
		ll += act*sp.log(pred) + (1-act)*sp.log(1-pred)
	return ll

def to_PIL(image):
	return Image.fromarray(np.asarray(image.transpose(1, 2, 0), dtype=np.uint8))

def to_theano(image):
	return np.asarray(image, dtype='float32').transpose(2, 0 ,1)

def visualizer(model):
	plot(model, to_file=ROOT + '/vis.png', show_shapes=True)

def dog_probab(y):
	return [pair[1] for pair in y]

def doubtful(pred):
	return (pred > lb and pred < lbub) or (pred < ub and pred > ublb)

def read_image(file_path):
	return to_theano(Image.open(file_path).convert('RGB').resize((img_height, img_width)))

def write_image(image, file_path):
	to_PIL(image).save(file_path)

def rotate(image, degrees):
	return image.rotate(degrees)

def resize(arr, h, w):
	return to_theano(to_PIL(arr).resize((h,w)))

def getVariations(image):
	img = Image.fromarray(np.asarray(image.transpose(1, 2, 0), dtype=np.uint8))
	images = []
	for degree in xrange(0, 360, 90):
		tmp = img.copy()
		tmp = rotate(tmp, degree)
		for x in xrange(0, img_width, step):
			for y in xrange(0, img_height, step):
				temp = tmp.copy()
				images.append(to_theano(temp.crop((x, y, x + zoom_width, y + zoom_height)).resize((img_height, 
							img_width))))
	
	return np.asarray(images)

def standardized(gen):
    mean, stddev = pickle.load(open('meanSTDDEV'))
    while 1:
        X = gen.next()
        for i in xrange(len(X)):
            X[i] = (X[i] - mean) / stddev
        yield X

def prep_data(images):
	batches = [images[i:min(len(images), i + mini_batch_sz)] 
				for i in xrange(0, len(images), mini_batch_sz)]

	for mini_batch in batches:
		data = np.ndarray((mini_batch_sz, channels, img_height, img_width), 
							dtype=np.float32)
		for i, image_file in enumerate(mini_batch):
			data[i] = read_image(image_file)
		yield data

def getConfident(preds):
	lessThanLB = [pred for pred in preds if pred < lb]
	greaterThanUB = [pred for pred in preds if pred > ub]
	if len(lessThanLB) != 0 and len(greaterThanUB) != 0:
		raise ValueError
	if len(lessThanLB) != 0:
		return min(lessThanLB)
	return max(greaterThanUB)

def kaggleTest(model):
	fnames = [TEST_DIR + fname for fname in listdir(TEST_DIR)]

	ids = [x[:-4] for x in [fname for fname in listdir(TEST_DIR)]]
	X = standardized(prep_data(fnames))
	i = 0
	saved = 50
	dog_probabs = []
	print 'Beginning prediction phase...'
	for mini_batch in X:
		y = dog_probab(model.predict(mini_batch))
		for j, pred in enumerate(y):
			pass
			# if doubtful(pred):
			# 	zoomPreds = dog_probab(model.predict(getVariations(mini_batch[j]), 
			# 					batch_size=mini_batch_sz))
			# 	y[j] = min(y[j], min(zoomPreds)) if y[j] < lbub else max(y[j], max(zoomPreds))
			#	saved -= 1
			#	write_image(mini_batch[j], '../failures/{}.jpg'.format(ids[i + j]))
			#	if saved == 0: return
		dog_probabs += y
		i += mini_batch_sz
		if i % 100 == 0: print "Finished {} of {}".format(i, len(fnames))

	with open(ROOT + '/out.csv','w') as f:
		f.write('id,label\n')
		for i,pred in zip(ids,dog_probabs):
			f.write('{},{}\n'.format(i,str(pred)))

def dumper(model,kind,fname=None):
	if not fname:
		fname = '{}/models/{}-{}.h5'.format(ROOT,
										str(datetime.now()).replace(' ','-'),kind)
	try:
		with open(fname,'w') as f:
			model.save(fname)
	except IOError:
		raise IOError('Unable to open: {}'.format(fname))
	return fname

def random_bright_shift(arr):
	img = to_PIL(arr)
	return to_theano(ImageEnhance.Brightness(img).enhance(np.random.uniform(0.37,1.63)))

def random_contrast_shift(arr):
	img = to_PIL(arr)
	return to_theano(ImageEnhance.Contrast(img).enhance(np.random.uniform(0.2,1.8)))

def blur(arr):
	img = to_PIL(arr)
	return to_theano(img.filter(ImageFilter.BLUR))