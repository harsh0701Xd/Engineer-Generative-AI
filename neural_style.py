# -*- coding: utf-8 -*-
"""Neural Style.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1DxFfkLFlYQv9VnZlZws1HuOzxmkYZ3un
"""

from google.colab import drive
drive.mount('/content/drive')

"""# Problem Statement

- To create a deep learning model capable of adapting an existing work to resemble the aesthetic of any art.

# Importing the necessary packages and dependencies
"""

# Commented out IPython magic to ensure Python compatibility.
import os
import sys
import scipy.io
import scipy.misc
import matplotlib.pyplot as plt
from matplotlib.pyplot import imshow
from PIL import Image
import numpy as np
import tensorflow as tf
import pprint
# %matplotlib inline

"""# Transfer Learning

- Neural Style Transfer (NST) uses a previously trained convolutional network, and builds on top of that. The idea of using a network trained on a different task and applying it to a new task is called transfer learning.

- We'll be using VGG-19, a 19-layer version of the VGG network. This model has already been trained on the very large ImageNet database, and has learned to recognize a variety of low level features (at the shallower layers) and high level features (at the deeper layers).
"""

tf.random.set_seed(272) # Keeping this value fixed
pp = pprint.PrettyPrinter(indent=4)
img_size = 400
vgg = tf.keras.applications.VGG19(include_top=False,input_shape=(img_size, img_size, 3),weights='/content/drive/MyDrive/Neural Style/vgg19_weights_tf_dim_ordering_tf_kernels_notop.h5')
vgg.trainable = False
pp.pprint(vgg)

"""# Neural Style Transfer (NST) algorithm involves the below three steps:

- building the content cost function $J_{content}(C,G)$
- second, building the style cost function $J_{style}(S,G)$
- finally, putting it all together to get $J(G) = \alpha J_{content}(C,G) + \beta J_{style}(S,G)$.

# Computing the Content Cost

## Making the Generated Image G Match the Content of Image C

* The shallower layers of a ConvNet tends to detect lower-level features such as <i>edges and simple textures</i>.
* The deeper layers tend to detect higher-level features such as more <i> complex textures and object classes</i>.

## Choosing the "middle" activation layer $a^{[l]}$ :

* We need the "generated" image G to have similar content as the input image C.
* We will choose a layer from somewhere in the middle of the network--neither too shallow nor too deep. This ensures that the network detects both higher-level and lower-level features.


## Propagating image "C:"

* We will set the image C as the input to the pretrained VGG network, and run forward propagation.  
* Let $a^{(C)}$ be the hidden layer activations in the layer we had chosen. This will be an $n_H \times n_W \times n_C$ tensor.

## Propagating image "G":
* We will repeat the above process with the image G: We will set G as the input, and run forward propagation.
* Let $a^{(G)}$ be the corresponding hidden layer activation.

# Provide the content/source image path location
"""

Content_file = "/content/drive/MyDrive/Neural Style/Content/25e21b4f3e.jpg"

content_image = Image.open(Content_file)
content_image

"""# Content Cost Function $J_{content}(C,G)$
One goal we should aim for when performing NST is for the content in generated image G to match the content of image C. A method to achieve this is to calculate the content cost function, which will be defined as:

$$J_{content}(C,G) =  \frac{1}{4 \times n_H \times n_W \times n_C}\sum _{ \text{all entries}} (a^{(C)} - a^{(G)})^2\tag{1} $$

* Here, $n_H, n_W$ and $n_C$ are the height, width and number of channels of the hidden layer you have chosen, and appear in a normalization term in the cost.
* $a^{(C)}$ and $a^{(G)}$ are the 3D volumes corresponding to a hidden layer's activations.
* In order to compute the cost $J_{content}(C,G)$, it might also be convenient to unroll these 3D volumes into a 2D matrix

## compute_content_cost

Computing the "content cost" using TensorFlow.

`a_G`: hidden layer activations representing content of the image G
<br>
`a_C`: hidden layer activations representing content of the image C

The 3 steps to implement the function are:

1. Retrieving dimensions from `a_G`
2. Unrolling `a_C` and `a_G`
3. Computing the content cost
"""

def compute_content_cost(content_output, generated_output):

    a_C = content_output[-1]
    a_G = generated_output[-1]

    m, n_H, n_W, n_C = a_G.get_shape().as_list()

    a_C_unrolled = tf.transpose(tf.reshape(a_C, shape=[m, -1, n_C]))
    a_G_unrolled = tf.transpose(tf.reshape(a_G, shape=[m, -1, n_C]))

    J_content =  (1 / (4 * n_H * n_W * n_C)) * tf.reduce_sum(tf.square(tf.subtract(a_C_unrolled, a_G_unrolled)))

    return J_content

"""## Computing the Style Cost

## Provide the Style image path location
"""

Style_file = "/content/drive/MyDrive/Neural Style/Styles/abstract_ward-jackson_6297.jpg"

"""# Style Matrix

## Gram matrix
* The style matrix is also called a "Gram matrix."
* In linear algebra, the Gram matrix G of a set of vectors $(v_{1},\dots ,v_{n})$ is the matrix of dot products, whose entries are ${\displaystyle G_{ij} = v_{i}^T v_{j} = np.dot(v_{i}, v_{j})  }$.
* In other words, $G_{ij}$ compares how similar $v_i$ is to $v_j$: If they are highly similar, we would expect them to have a large dot product, and thus for $G_{ij}$ to be large.

# Computing Gram matrix $G_{gram}$

We will compute the Style matrix by multiplying the "unrolled" filter matrix with its transpose:


$$\mathbf{G}_{gram} = \mathbf{A}_{unrolled} \mathbf{A}_{unrolled}^T$$

## $G_{(gram)ij}$: Correlation
The result is a matrix of dimension $(n_C,n_C)$ where $n_C$ is the number of filters (channels). The value $G_{(gram)i,j}$ measures how similar the activations of filter $i$ are to the activations of filter $j$.

## $G_{(gram),ii}$: Prevalence of patterns or textures
* The diagonal elements $G_{(gram)ii}$ measure how "active" a filter $i$ is.
* For example, suppose filter $i$ is detecting vertical textures in the image. Then $G_{(gram)ii}$ measures how common  vertical textures are in the image as a whole.
* If $G_{(gram)ii}$ is large, this means that the image has a lot of vertical texture.


By capturing the prevalence of different types of features ($G_{(gram)ii}$), as well as how much different features occur together ($G_{(gram)ij}$), the Style matrix $G_{gram}$ measures the style of an image.

Using TensorFlow, we will implement a function that computes the Gram matrix of a matrix A.
The formula is: The gram matrix of A is $G_A = AA^T$.
"""

example = Image.open(Style_file)
example

def gram_matrix(A):

    GA = tf.matmul(A, A, transpose_b=True)

    return GA

"""# compute_layer_style_cost
Computing the style cost for a single layer.

The 3 steps to implement this function are:
1. Retrieve dimensions from the hidden layer activations a_G
2. Unroll the hidden layer activations a_S and a_G into 2D matrices
3. Compute the Style matrix of the images S and G
4. Compute the Style cost
"""

def compute_layer_style_cost(a_S, a_G):

    m, n_H, n_W, n_C = a_G.get_shape().as_list()


    a_S = tf.transpose(tf.reshape(a_S, shape=[-1, n_C]))
    a_G = tf.transpose(tf.reshape(a_G, shape=[-1, n_C]))


    GS = gram_matrix(a_S)
    GG = gram_matrix(a_G)


    J_style_layer = (1 / (4 * n_C **2 * (n_H * n_W) **2)) * tf.reduce_sum(tf.square(tf.subtract(GS, GG)))


    return J_style_layer

"""# Style Weights

* By default, we have given each layer equal weight, and the weights add up to 1.  ($\sum_{l}^L\lambda^{[l]} = 1$)
* But we can get better results if we "merge" style costs from several different layers. Each layer can be given weights ($\lambda^{[l]}$) that reflect how much each layer will contribute to the style.

# Listing the layer names:
"""

for layer in vgg.layers:
    print(layer.name)

"""Choosing the layers to represent the style of the image and assign style costs"""

STYLE_LAYERS = [
    ('block1_conv1', 0.2),
    ('block2_conv1', 0.2),
    ('block3_conv1', 0.2),
    ('block4_conv1', 0.2),
    ('block5_conv1', 0.2)]

"""We can combine the style costs for different layers as follows:

$$J_{style}(S,G) = \sum_{l} \lambda^{[l]} J^{[l]}_{style}(S,G)$$

where the values for $\lambda^{[l]}$ are given in `STYLE_LAYERS`.

# compute_style_cost

For each layer:
* Select the activation (the output tensor) of the current layer.
* Get the style of the style image "S" from the current layer.
* Get the style of the generated image "G" from the current layer.
* Compute the "style cost" for the current layer
* Add the weighted style cost to the overall style cost (J_style)
"""

def compute_style_cost(style_image_output, generated_image_output, STYLE_LAYERS=STYLE_LAYERS):

    J_style = 0

    a_S = style_image_output[:-1]

    a_G = generated_image_output[:-1]
    for i, weight in zip(range(len(a_S)), STYLE_LAYERS):

        J_style_layer = compute_layer_style_cost(a_S[i], a_G[i])


        J_style += weight[1] * J_style_layer

    return J_style

"""# Defining the Total Cost to Optimize

Finally, we will create a cost function that minimizes both the style and the content cost. The formula is:

$$J(G) = \alpha J_{content}(C,G) + \beta J_{style}(S,G)$$

We will Implement the total cost function which includes both the content cost and the style cost.
"""

@tf.function()
def total_cost(J_content, J_style, alpha = 10, beta = 80):

    J = alpha * J_content + beta * J_style

    return J

"""The total cost is a linear combination of the content cost $J_{content}(C,G)$ and the style cost $J_{style}(S,G)$.
$\alpha$ and $\beta$ are hyperparameters that control the relative weighting between content and style.

## Solving the Optimization Problem

### Loading the Content Image
"""

content_image = np.array(Image.open(Content_file).resize((img_size, img_size)))
content_image = tf.constant(np.reshape(content_image, ((1,) + content_image.shape)))

print(content_image.shape)
imshow(content_image[0])
plt.show()

"""# Loading the Style Image"""

style_image =  np.array(Image.open(Style_file).resize((img_size, img_size)))
style_image = tf.constant(np.reshape(style_image, ((1,) + style_image.shape)))

print(style_image.shape)
imshow(style_image[0])
plt.show()

"""# Randomly Initializing the Image to be Generated

* The generated image can be slightly correlated with the content image. Since by initializing the pixels of the generated image to be mostly noisy but slightly correlated with the content image will help the content of the "generated" image more rapidly match the content of the "content" image.
"""

generated_image = tf.Variable(tf.image.convert_image_dtype(content_image, tf.float32))
noise = tf.random.uniform(tf.shape(generated_image), -0.25, 0.25)
generated_image = tf.add(generated_image, noise)
generated_image = tf.clip_by_value(generated_image, clip_value_min=0.0, clip_value_max=1.0)

print(generated_image.shape)
imshow(generated_image.numpy()[0])
plt.show()

"""# Loading the Pre-trained VGG19 Model"""

def get_layer_outputs(vgg, layer_names):

    outputs = [vgg.get_layer(layer[0]).output for layer in layer_names]

    model = tf.keras.Model([vgg.input], outputs)
    return model

"""Now, we define the content layer and build the model."""

content_layer = [('block5_conv4', 1)]

vgg_model_outputs = get_layer_outputs(vgg, STYLE_LAYERS + content_layer)

"""Saving the outputs for the content and style layers in separate variables."""

content_target = vgg_model_outputs(content_image)  # Content encoder
style_targets = vgg_model_outputs(style_image)     # Style encoder

"""# Compute Total Cost

## Compute the Content image Encoding (a_C)

We've built the model, and now to compute the content cost, we will encode our content image using the appropriate hidden layer activations. We will set this encoding to the variable `a_C`. Later we do the same for the generated image, by setting the variable `a_G` to be the appropriate hidden layer activations. We will use layer `block5_conv4` to compute the encoding.
"""

preprocessed_content =  tf.Variable(tf.image.convert_image_dtype(content_image, tf.float32))
a_C = vgg_model_outputs(preprocessed_content)


a_G = vgg_model_outputs(generated_image)


J_content = compute_content_cost(a_C, a_G)

print(J_content)

"""# Compute the Style image Encoding (a_S)

The code below sets a_S to be the tensor giving the hidden layer activation for `STYLE_LAYERS` using our style image.
"""

preprocessed_style =  tf.Variable(tf.image.convert_image_dtype(style_image, tf.float32))
a_S = vgg_model_outputs(preprocessed_style)


J_style = compute_style_cost(a_S, a_G)
print(J_style)

"""Below are the utils that we will need to display the images generated by the style transfer model."""

def clip_0_1(image):

    return tf.clip_by_value(image, clip_value_min=0.0, clip_value_max=1.0)

def tensor_to_image(tensor):

    tensor = tensor * 255
    tensor = np.array(tensor, dtype=np.uint8)
    if np.ndim(tensor) > 3:
        assert tensor.shape[0] == 1
        tensor = tensor[0]
    return Image.fromarray(tensor)

"""# train_step

## We implement the train_step() function for transfer learning

* We will be using the Adam optimizer to minimize the total cost `J`, learning rate of 0.01, `alpha = 10` and `beta = 40`.
"""

optimizer = tf.keras.optimizers.Adam(learning_rate=0.0001)

@tf.function()
def train_step(generated_image):
    with tf.GradientTape() as tape:

        a_G = vgg_model_outputs(generated_image)


        J_style = compute_style_cost(a_S, a_G)


        J_content = compute_content_cost(a_C, a_G)

        J = total_cost(J_content, J_style)


    grad = tape.gradient(J, generated_image)

    optimizer.apply_gradients([(grad, generated_image)])
    generated_image.assign(clip_0_1(generated_image))
    return J

generated_image = tf.Variable(generated_image)

train_step_test(train_step, generated_image)

"""# Model training"""

epochs = 5000
for i in range(epochs):
    train_step(generated_image)
    if i % 250 == 0:
        print(f"Epoch {i} ")
    if i % 250 == 0:
        image = tensor_to_image(generated_image)
        imshow(image)
        image.save(f"output/image_{i}.jpg")
        plt.show()

"""Visualising the results!"""

fig = plt.figure(figsize=(16, 4))
ax = fig.add_subplot(1, 3, 1)
imshow(content_image[0])
ax.title.set_text('Content image')
ax = fig.add_subplot(1, 3, 2)
imshow(style_image[0])
ax.title.set_text('Style image')
ax = fig.add_subplot(1, 3, 3)
imshow(generated_image[0])
ax.title.set_text('Generated image')
plt.show()

"""## Possible hyperparameter tunings

- Selecting different layers to represent the style, by redefining `STYLE_LAYERS`
- Altering the number of iterations we want to run the algorithm, by changing `epochs`
- Altering the relative weight of content versus style by altering alpha and beta values
"""