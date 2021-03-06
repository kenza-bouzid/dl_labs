from six.moves import cPickle
from keras.utils.np_utils import to_categorical
from sklearn.metrics import accuracy_score
from sklearn.utils import shuffle
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm


def softmax(x):
    """ Standard definition of the softmax function """
    return np.exp(x) / np.sum(np.exp(x), axis=0)

def loadData(filename, reshape=False, clipping=False):
    """ Loads data and creates one hot encoded labels """

    f = open('Dataset/cifar-10-batches-py/'+filename, 'rb')
    datadict = cPickle.load(f, encoding='latin1')
    f.close()

    X = datadict["data"]
    y = datadict['labels']

    if reshape:
        X = X.reshape(10000, 3, 32, 32).transpose(0, 2, 3, 1).astype(np.uint8)

    if clipping:
        X = X.astype(np.float32)
        X /= 255.0
        X = X.T

    y = np.array(y)
    # One hot Encode labels
    Y = to_categorical(y, num_classes=10)
    Y = Y.T

    return X, y, Y


def plotCifar(X, Y):
    """ Util function to plot cifar original images along with their labels """
    fig, axes1 = plt.subplots(5, 5, figsize=(12, 12))
    print(X.shape)
    for j in range(5):
        for k in range(5):
            i = np.random.choice(range(len(X)))
            axes1[j][k].set_axis_off()
            axes1[j][k].imshow(X[i:i+1][0])
            axes1[j][k].set_title(Y[i:i+1])


def EvaluateClassifier(x, W, b):
    z = W @ x + b
    return softmax(z)


def ComputeCost(X, Y, W, b, _lambda):
    """ Computes the cost function: cross entropy loss + L2 regularization """
    P = EvaluateClassifier(X, W, b)
    l = -np.log(np.sum(np.multiply(Y, P), axis=0))
    r = np.linalg.norm(W)**2
    J = np.sum(l)/X.shape[1] + _lambda*r
    return J


def ComputeAccuracy(X, y, W, b):
    """ Computes the prediction accuracy of a given state of the network """ 
    P = EvaluateClassifier(X, W, b)
    y_pred = np.argmax(P, axis=0)
    return accuracy_score(y, y_pred)


def ComputeGradients(X, Y, P, W, _lambda):
    """ Computes gradients for cross entropy loss """
    G = -(Y - P)
    nb = X.shape[1]
    grad_W = G @ X.T / nb + 2 * _lambda * W
    grad_b = np.sum(G, axis=1) / nb

    return grad_W, grad_b

def ComputeGradientsHinge(X, Y, W, b, _lambda):
    """ Computes gradients for hinge loss """
    n_batch = X.shape[1]
    scores = W @ X + b
    yi_scores = scores[np.argmax(Y, axis=0), np.arange(X.shape[1])]
    
    margins = np.maximum(0, scores - np.asarray(yi_scores) + 1)
    margins[np.argmax(Y, axis=0), np.arange(X.shape[1])] = 0

    binary = margins
    binary[margins > 0] = 1
    row_sum = np.sum(binary, axis=0)
    binary[np.argmax(Y, axis=0), np.arange(X.shape[1])] = -row_sum.T
    
    grad_W = binary @ X.T / n_batch + 2 * _lambda * W
    gradb = np.sum(binary, axis=1)/n_batch

    return grad_W, gradb


def compare_gradients(ga, gn, eps):
    """ Compares analytical and numerical gradients given a certain epsilon """
    K, d = ga.shape
    rerr = np.zeros((K, d))
    for i in range(K):
        for j in range(d):
            rerr[i, j] = abs(ga[i, j] - gn[i, j]) / \
                max(eps, abs(ga[i, j]) + abs(gn[i, j]))
    return rerr


def history(X, Y, y, X_val, Y_val, y_val, epoch, W, b, _lambda, train_loss, val_loss, train_acc, val_acc, verbose=True):
    """ Creates history of the training """ 
    J_train = ComputeCost(X, Y, W, b, _lambda)
    J_val = ComputeCost(X_val, Y_val, W, b, _lambda)

    t_acc = ComputeAccuracy(X, y, W, b)
    v_acc = ComputeAccuracy(X_val, y_val, W, b)

    if verbose:
        print(
            f'Epoch {epoch}: train_acc={t_acc} | val_acc={v_acc} | train_loss={J_train} | val_loss={J_val}')

    train_loss.append(J_train)
    val_loss.append(J_val)
    train_acc.append(t_acc)
    val_acc.append(v_acc)


def minibatchGD(X, Y, y,  X_val, Y_val, y_val, GDparams, W, b, verbose=True, patience=0, annealing=False, reorder=False, loss="cross_entropy", experiment="mandatory"):
    """ Performas minibatch gradient descent """
    _, n = X.shape

    train_loss, val_loss = [], []
    train_acc, val_acc = [], []

    epochs, batch_size, eta, _lambda = GDparams["n_epochs"], GDparams[
        "n_batch"], GDparams["eta"],  GDparams["lambda"]

    if annealing:
        gamma = GDparams['eta_decay']
        freq = GDparams['eta_decay_freq']

    history(X, Y, y,  X_val, Y_val, y_val, 0, W, b,
            _lambda, train_loss, val_loss, train_acc, val_acc, verbose)

    for epoch in tqdm(range(epochs)):
        if reorder:
            X, Y, y = shuffle(X.T, Y.T, y.T, random_state=epoch)
            X, Y, y = X.T, Y.T, y.T

        for j in range(n//batch_size):
            j_start = j * batch_size
            j_end = (j+1) * batch_size
            X_batch = X[:, j_start:j_end]
            Y_batch = Y[:, j_start:j_end]

            P_batch = EvaluateClassifier(X_batch, W, b)
            if loss == "cross_entropy":
                grad_W, grad_b = ComputeGradients(
                X_batch, Y_batch, P_batch, W, _lambda)
            else:
                grad_W, grad_b = ComputeGradientsHinge(
                    X_batch, Y_batch, W, b, _lambda)

            W -= eta * grad_W
            b -= eta * grad_b.reshape(len(b), 1)

        history(X, Y, y,  X_val, Y_val, y_val, epoch, W,
                b, _lambda, train_loss, val_loss, train_acc, val_acc, verbose)

        if early_stopping(val_loss, patience) and patience > 0:
            print(f"Early Stopping @ Epoch: {epoch}")
            break

        if annealing:
            eta = update_eta(eta, gamma, freq, epoch)

    backup(GDparams, W, b, train_loss, val_loss, train_acc,
           val_acc, patience=patience, annealing=annealing, reorder=reorder, experiment=experiment)
    
    train_loss = np.array(train_loss)
    val_loss = np.array(val_loss)
    train_acc = np.array(train_acc)
    val_acc = np.array(val_acc)

    return W, b, train_loss, val_loss, train_acc, val_acc


def backup(GDparams, W, b, train_loss, val_loss, train_acc, val_acc, patience=0, annealing=False, reorder=False, experiment="mandatory"):
    """ Saves networks params in order to be able to reuse it """
    epochs, batch_size, eta, _lambda = GDparams["n_epochs"], GDparams[
        "n_batch"], GDparams["eta"],  GDparams["lambda"]
    np.save(
        f'History/{experiment}_weights_{epochs}_{batch_size}_{eta}_{_lambda}_{patience}_{int(reorder)}_{int(annealing)}.npy', W)
    np.save(
        f'History/{experiment}_bias_{epochs}_{batch_size}_{eta}_{_lambda}_{patience}_{int(reorder)}_{int(annealing)}.npy', b)
    np.save(
        f'History/{experiment}_train_loss_{epochs}_{batch_size}_{eta}_{_lambda}_{patience}_{int(reorder)}_{int(annealing)}.npy', train_loss)
    np.save(
        f'History/{experiment}_val_loss_{epochs}_{batch_size}_{eta}_{patience}_{int(reorder)}_{int(annealing)}.npy', val_loss)
    np.save(
        f'History/{experiment}_train_acc_{epochs}_{batch_size}_{eta}_{_lambda}_{patience}_{int(reorder)}_{int(annealing)}.npy', train_acc)
    np.save(
        f'History/{experiment}_val_acc_{epochs}_{batch_size}_{eta}_{patience}_{int(reorder)}_{int(annealing)}.npy', val_acc)


def montage(W, GDparams, patience=0, annealing=False, reorder=False, experiment="mandatory"):
    """ Display the image for each label in W """
    epochs, batch_size, eta, _lambda = GDparams["n_epochs"], GDparams[
        "n_batch"], GDparams["eta"],  GDparams["lambda"]
    _, ax = plt.subplots(2, 5)
    for i in range(2):
        for j in range(5):
            im = W[i*5+j, :].reshape(32, 32, 3, order='F')
            sim = (im-np.min(im[:]))/(np.max(im[:])-np.min(im[:]))
            sim = sim.transpose(1, 0, 2)
            ax[i][j].imshow(sim, interpolation='nearest')
            ax[i][j].set_title("y="+str(5*i+j))
            ax[i][j].axis('off')
    plt.savefig(
        f'History/{experiment}_weights_{epochs}_{batch_size}_{eta}_{_lambda}_{patience}_{int(reorder)}_{int(annealing)}.png')
    plt.show()


def plot_metric(train_loss, val_loss, GDparams, patience=0, annealing=False, reorder=False, type="loss", experiment="mandatory"):
    """ Plots a given metric (loss or accuracy) """
    epochs, batch_size, eta, _lambda = GDparams["n_epochs"], GDparams[
        "n_batch"], GDparams["eta"],  GDparams["lambda"]

    plt.plot(train_loss, label=f"Train {type}")
    plt.plot(val_loss, label=f"Validation {type}")
    plt.xlabel("epochs")
    plt.ylabel(type)
    plt.title(f"Monitoring of {type} during {len(val_loss)} epochs.")
    plt.legend()
    plt.savefig(
        f'History/{experiment}_hist_{type}_{epochs}_{batch_size}_{eta}_{_lambda}_{patience}_{int(reorder)}_{int(annealing)}.png')
    plt.show()


def early_stopping(val_loss, patience):
    """ Gives an early stopping status """
    if len(val_loss) > 2*patience:
        return all(x < y for x, y in zip(val_loss[-patience:], val_loss[-patience+1:]))
    return False


def update_eta(eta, gamma, freq, epoch):
    """ Performs Learning rate decay """
    if epoch % freq == 0:
        eta = gamma*eta
    return eta
