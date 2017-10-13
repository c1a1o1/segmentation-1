import tensorflow as tf
import numpy as np
import os, glob, cv2


def weight_variable(shape, name=None):
    initial = tf.truncated_normal(shape, stddev=0.01)
    return tf.Variable(initial, name=name)

def bias_variable(shape, name=None):
    initial = tf.constant(0., shape=shape)
    return tf.Variable(initial, name=name)

""" return 4-D tensor with shape = (batchsize, ...) """
def load_images(paths, batchsize, crop_size):
    ## use numpy
    tensor = []
    imglist = np.random.choice(paths, batchsize)
    for imgp in imglist:
        tensor.append(cv2.imread(imgp)[:,:,::-1]) ## BGR --> RGB

    ## Apply a crop
    fx = lambda ix: np.random.randint(ix.shape[0]-crop_size)
    fy = lambda ix: np.random.randint(ix.shape[1]-crop_size)
    for k in range(batchsize):
        xx = fx(tensor[k])
        yy = fx(tensor[k])
        tensor[k] = tensor[k][xx:xx+crop_size, yy:yy+crop_size,:]

    ## Also treat images like they're the same size
    tensor = [np.expand_dims(x,0) for x in tensor]
    tensor = np.concatenate(tensor, 0).astype(np.float32)
    tensor /= tensor.max()

    print 'Loaded {} tensor : {}, {}\t{}'.format(tensor.shape,
        tensor.min(), tensor.max(), tensor.dtype)
    return tensor

"""
Implements a threaded queue for reading images from disk given filenames
Since this is for segmentation, we have to also read masks in the same order

Assume the images and masks are named similarly and are in different folders
"""
class ImageMaskDataSet(object):
    def __init__(self,
                 image_dir,
                 mask_dir,
                 image_names = None, ## /Unused args. plan to auto-split train-val
                 mask_names = None,
                 split_train_val = False, ## /end unused args
                 n_classes = 2,
                 batch_size= 96,
                 crop_size =256,
                 capacity  =5000,
                 image_ext ='jpg',
                 mask_ext  ='png',
                 seed      =5555,
                 threads   =2):


        self.image_names = tf.convert_to_tensor(sorted(glob.glob(
        os.path.join(image_dir, '*.'+image_ext) )))
        self.mask_names  = tf.convert_to_tensor(sorted(glob.glob(
        os.path.join(mask_dir, '*.'+mask_ext) )))
        print 'Dataset image, mask lists populated'
        print '{} image files starting with {}'.format(self.image_names.shape, self.image_names[0])
        print '{} masks files starting with {}'.format(self.mask_names.shape, self.mask_names[0])

        print 'Setting data hyperparams'
        self.batch_size = batch_size
        self.crop_size  = crop_size
        self.capacity  = capacity
        self.n_classes = n_classes
        self.threads = threads

        ## Set random seed to shuffle the same way..
        print 'Setting up image, mask queues'
        self.feature_queue = tf.train.string_input_producer(
            self.image_names,
            shuffle=True,
            seed=seed )
        self.mask_queue    = tf.train.string_input_producer(
            self.mask_names,
            shuffle=True,
            seed=seed )

        self.image_reader = tf.WholeFileReader()
        self.mask_reader  = tf.WholeFileReader()
        # self.image_op, self.mask_op = self.setup_image_mask_ops()
        self._setup_image_mask_ops()


    def set_tf_sess(self, sess):
        self.sess = sess

    def _setup_image_mask_ops(self):
        print 'Setting up image and mask retrieval ops'
        with tf.name_scope('ImageMaskDataSet'):
            image_key, image_file = self.image_reader.read(self.feature_queue)
            image_op = tf.image.decode_image(image_file)

            mask_key, mask_file = self.image_reader.read(self.mask_queue)
            mask_op = tf.image.decode_image(mask_file)

            image_op, mask_op = self.preprocessing(image_op, mask_op)
            image_op, mask_op = tf.train.shuffle_batch([image_op, mask_op],
                batch_size = self.batch_size,
                capacity   = self.capacity,
                min_after_dequeue = 100,
                num_threads = self.threads,
                name = 'Dataset')

            self.image_op = image_op
            self.mask_op = mask_op


    def preprocessing(self, image, mask):
        image = tf.divide(image, 255)
        mask  = tf.divide(mask, 255)
        ## Stack so that transforms are applied the right way
        image_mask = tf.concat([image, mask], 2)
        # image_mask = tf.Print(image_mask, [image_mask, 'preprocessing image_mask'])

        ## Perform a random crop
        image_mask = tf.random_crop(image_mask,
            [self.crop_size, self.crop_size, 4])

        image, mask = tf.split(image_mask, [3,1], axis=2)

        ## Convert to flat, onehot
        # mask = tf.reshape(tensor=mask, shape=(-1, 1))
        # mask = tf.one_hot(mask, self.n_classes)

        return image, mask

    def get_batch(self):
        # image, mask = tf.train.shuffle_batch([self.image_op, self.mask_op],
        #     batch_size = self.batch_size,
        #     capacity   = self.capacity,
        #     min_after_dequeue = 1000)

        # print 'Getting batch from dataset'
        image, mask = self.sess.run([self.image_op, self.mask_op])

        return image, mask
#/end ImageMaskDataSet






"""
end file
"""