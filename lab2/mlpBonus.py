
from collections import Counter
from sklearn.utils import shuffle
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score
import numpy as np
from tqdm import tqdm
from collections import defaultdict


def softmax(x):
    """ Standard definition of the softmax function """
    return np.exp(x) / np.sum(np.exp(x), axis=0)


class Layer():
    def __init__(self, d_in, d_out, W, b, grad_W, grad_b, x):
        self.d_in = d_in
        self.d_out = d_out
        self.W = W
        self.b = b
        self.grad_W = grad_W
        self.grad_b = grad_b
        self.input = input


class MLP():
    def __init__(self, k=2, dims=[3072, 50, 10], lamda=0, seed=42) -> None:
        np.random.seed(seed)
        self.seed = seed
        self.k = k
        self.lamda = lamda
        self.dims = dims
        self.layers = []
        for i in range(k):
            d_in, d_out = self.dims[i], self.dims[i+1]
            self.layers.append(Layer(d_in, d_out, np.random.normal(
                0, 1/np.sqrt(d_in), (d_out, d_in)), np.zeros((d_out, 1)), None, None, None))

        self.train_loss, self.val_loss = [], []
        self.train_cost, self.val_cost = [], []
        self.train_acc, self.val_acc = [], []
        self.etas = []

    def forward_pass(self, X):
        input = X.copy()
        for layer in self.layers:
            layer.input = input.copy()
            input = np.maximum(
                0, layer.W @ layer.input + layer.b)
        return softmax(layer.W @ layer.input + layer.b)

    def compute_cost(self, X, Y):
        """ Computes the cost function: cross entropy loss + L2 regularization """
        P = self.forward_pass(X)
        loss = np.log(np.sum(np.multiply(Y, P), axis=0))
        loss = - np.sum(loss)/X.shape[1]
        r = np.sum([np.linalg.norm(layer.W) ** 2 for layer in self.layers])
        cost = loss + self.lamda * r
        return loss, cost

    def compute_gradients(self, X, Y, P):
        G = - (Y - P)
        nb = X.shape[1]

        for layer in reversed(self.layers):
            layer.grad_W = G @ layer.input.T / nb + \
                2 * self.lamda * layer.W
            layer.grad_b = (
                np.sum(G, axis=1) / nb).reshape(layer.d_out, 1)
            G = layer.W.T @ G
            G = np.multiply(G, np.heaviside(layer.input, 0))

    def update_parameters(self, eta=1e-2):
        for layer in self.layers:
            layer.W -= eta * layer.grad_W
            layer.b -= eta * layer.grad_b

    def compute_gradients_num(self, X_batch, Y_batch, h=1e-5):
        """ Numerically computes the gradients of the weight and bias parameters
        Args:
            X_batch (np.ndarray): data batch matrix (n_dims, n_samples)
            Y_batch (np.ndarray): one-hot-encoding labels batch vector (n_classes, n_samples)
            h            (float): marginal offset
        Returns:
            grad_W  (np.ndarray): the gradient of the weight parameter
            grad_b  (np.ndarray): the gradient of the bias parameter
        """
        grads = {}
        for j, layer in enumerate(self.layers):
            selfW = layer.W
            selfB = layer.b
            grads['W' + str(j)] = np.zeros(selfW.shape)
            grads['b' + str(j)] = np.zeros(selfB.shape)

            b_try = np.copy(selfB)
            for i in range(selfB.shape[0]):
                layer.b = np.copy(b_try)
                layer.b[i] += h
                _, c1 = self.compute_cost(X_batch, Y_batch)
                layer.b = np.copy(b_try)
                layer.b[i] -= h
                _, c2 = self.compute_cost(X_batch, Y_batch)
                grads['b' + str(j)][i] = (c1-c2) / (2*h)
            layer.b = b_try

            W_try = np.copy(selfW)
            for i in np.ndindex(selfW.shape):
                layer.W = np.copy(W_try)
                layer.W[i] += h
                _, c1 = self.compute_cost(X_batch, Y_batch)
                layer.W = np.copy(W_try)
                layer.W[i] -= h
                _, c2 = self.compute_cost(X_batch, Y_batch)
                grads['W' + str(j)][i] = (c1-c2) / (2*h)
            layer.W = W_try

        return grads

    def compare_gradients(self, X, Y, eps=1e-10, h=1e-5):
        """ Compares analytical and numerical gradients given a certain epsilon """
        gn = self.compute_gradients_num(X, Y, h)
        rerr_w, rerr_b = [], []
        aerr_w, aerr_b = [], []

        def _rel_error(x, y, eps): return np.abs(
            x-y)/max(eps, np.abs(x)+np.abs(y))

        def rel_error(g1, g2, eps):
            vfunc = np.vectorize(_rel_error)
            return np.mean(vfunc(g1, g2, eps))

        for i, layer in enumerate(self.layers):
            rerr_w.append(rel_error(layer.grad_W, gn[f'W{i}'], eps))
            rerr_b.append(rel_error(layer.grad_b, gn[f'b{i}'], eps))
            aerr_w.append(np.mean(abs(layer.grad_W - gn[f'W{i}'])))
            aerr_b.append(np.mean(abs(layer.grad_b - gn[f'b{i}'])))

        return rerr_w, rerr_b, aerr_w, aerr_b

    def compute_accuracy(self, X, y):
        """ Computes the prediction accuracy of a given state of the network """
        P = self.forward_pass(X)
        y_pred = np.argmax(P, axis=0)
        return accuracy_score(y, y_pred)

    def mini_batch_gd(self, data, GDparams, verbose=True, backup=False):
        """ Performas minibatch gradient descent """

        X, Y, y = data["X_train"], data["Y_train"], data["y_train"]

        _, n = X.shape

        epochs, batch_size, eta = GDparams["n_epochs"], GDparams["n_batch"], GDparams["eta"]

        self.history(data, 0, verbose, cyclic=False)

        for epoch in tqdm(range(epochs)):

            X, Y, y = shuffle(X.T, Y.T, y.T, random_state=epoch)
            X, Y, y = X.T, Y.T, y.T

            for j in range(n//batch_size):
                j_start = j * batch_size
                j_end = (j+1) * batch_size
                X_batch = X[:, j_start:j_end]
                Y_batch = Y[:, j_start:j_end]

                P_batch = self.forward_pass(X_batch)

                self.compute_gradients(X_batch, Y_batch, P_batch)

                self.update_parameters(eta)

            self.history(data, epoch, verbose, cyclic=False)

        if backup:
            self.backup(GDparams)

    def cyclic_learning(self, data, GDparams, verbose=True, backup=False, jitter=False):
        """ Performas minibatch gradient descent """
        X, Y, y = data["X_train"], data["Y_train"], data["y_train"]

        _, n = X.shape

        n_cycles, batch_size, eta_min, eta_max, ns, freq, exp = GDparams["n_cycles"], GDparams[
            "n_batch"], GDparams["eta_min"], GDparams["eta_max"], GDparams["ns"], GDparams['freq'], GDparams['exp']

        eta = eta_min
        t, c = 0, 0

        epochs = batch_size * 2 * ns * n_cycles // n

        for epoch in tqdm(range(epochs)):

            X, Y, y = shuffle(X.T, Y.T, y.T, random_state=epoch)
            X, Y, y = X.T, Y.T, y.T

            for j in range(n//batch_size):
                j_start = j * batch_size
                j_end = (j+1) * batch_size
                X_batch = X[:, j_start:j_end]
                Y_batch = Y[:, j_start:j_end]
                X_batch_copy = X_batch.copy()
                
                if jitter and np.random.random() > 0.5:
                    X_batch = self.random_jitter(X_batch, flip=0)
                
                P_batch = self.forward_pass(X_batch)

                self.compute_gradients(X_batch, Y_batch, P_batch)
                self.update_parameters(eta)

                X_batch = X_batch_copy

                if t % (2*ns/freq) == 0:
                    self.history(data, t, verbose)

                if t <= ns:
                    eta = eta_min + t/ns * (eta_max - eta_min)
                else:
                    eta = eta_max - (t - ns)/ns * (eta_max - eta_min)

                t = (t+1) % (2*ns)
                if t == 0 and exp == "ensemble_learning":
                    if verbose:
                        print(f"Cycle {c} saved")
                    self.backup_cyclic(GDparams, cycle=c)
                    c += 1
        if backup:
            self.backup_cyclic(GDparams)

    def history(self, data, epoch, verbose=True, cyclic=True):
        """ Creates history of the training """

        X, Y, y, X_val, Y_val, y_val = data["X_train"], data["Y_train"], data[
            "y_train"], data["X_val"], data["Y_val"], data["y_val"]

        t_loss, t_cost = self.compute_cost(X, Y)
        v_loss, v_cost = self.compute_cost(X_val, Y_val)

        t_acc = self.compute_accuracy(X, y)
        v_acc = self.compute_accuracy(X_val, y_val)

        if verbose:
            pref = "Update Step " if cyclic else "Epoch "
            print(
                f'{pref}{epoch}: train_acc={t_acc} | val_acc={v_acc} | train_loss={t_loss} | val_loss={v_loss} | train_cost={t_cost} | val_cost={v_cost}')

        self.train_loss.append(t_loss)
        self.val_loss.append(v_loss)
        self.train_cost.append(t_cost)
        self.val_cost.append(v_cost)
        self.train_acc.append(t_acc)
        self.val_acc.append(v_acc)

    def backup(self, GDparams):
        """ Saves networks params in order to be able to reuse it """

        epochs, batch_size, eta, exp = GDparams["n_epochs"], GDparams["n_batch"], GDparams["eta"], GDparams["exp"]

        np.save(
            f'History/{exp}_layers_{epochs}_{batch_size}_{eta}_{self.lamda}_{self.seed}.npy', self.layers)

        hist = {"train_loss": self.train_loss, "train_acc": self.train_acc, "train_cost": self.train_cost,
                "val_loss": self.val_loss, "val_acc": self.val_acc, "val_cost": self.val_cost}

        np.save(
            f'History/{exp}_hist_{epochs}_{batch_size}_{eta}_{self.lamda}_{self.seed}.npy', hist)

    def backup_cyclic(self, GDparams, cycle=-1):
        """ Saves networks params in order to be able to reuse it for cyclic learning"""

        n_cycles, batch_size, eta_min, eta_max, ns, exp = GDparams["n_cycles"], GDparams[
            "n_batch"], GDparams["eta_min"], GDparams["eta_max"], GDparams["ns"], GDparams["exp"]

        np.save(
            f'History/{exp}_layers_{n_cycles}_{cycle}_{batch_size}_{eta_min}_{eta_max}_{ns}_{self.lamda}_{self.seed}.npy', self.layers)

        hist = {"train_loss": self.train_loss, "train_acc": self.train_acc, "train_cost": self.train_cost,
                "val_loss": self.val_loss, "val_acc": self.val_acc, "val_cost": self.val_cost}

        np.save(
            f'History/{exp}_hist_{n_cycles}_{cycle}_{batch_size}_{eta_min}_{eta_max}_{ns}_{self.lamda}_{self.seed}.npy', hist)

    def plot_metric(self, GDparams, metric="loss", cyclic=True):
        """ Plots a given metric (loss or accuracy) """

        if cyclic:
            n_cycles, batch_size, eta_min, eta_max, ns = GDparams["n_cycles"], GDparams[
                "n_batch"], GDparams["eta_min"], GDparams["eta_max"], GDparams["ns"]
        else:
            epochs, batch_size, eta = GDparams["n_epochs"], GDparams["n_batch"], GDparams["eta"]

        batch_size, exp = GDparams["n_batch"], GDparams['exp']

        if metric == "loss":
            plt.ylim(0, 3)
            plt.plot(self.train_loss, label=f"Train {metric}")
            plt.plot(self.val_loss, label=f"Validation {metric}")
        elif metric == "accuracy":
            plt.ylim(0, 0.8)
            plt.plot(self.train_acc, label=f"Train {metric}")
            plt.plot(self.val_acc, label=f"Validation {metric}")
        else:
            plt.ylim(0, 4)
            plt.plot(self.train_cost, label=f"Train {metric}")
            plt.plot(self.val_cost, label=f"Validation {metric}")

        plt.xlabel("epochs")
        plt.ylabel(metric)
        if cyclic:
            plt.title(f"Monitoring of {metric} during {n_cycles} cycles.")
        else:
            plt.title(f"Monitoring of {metric} during {epochs} epochs.")
        plt.legend()
        if cyclic:
            plt.savefig(
                f'History/{exp}_{metric}_{n_cycles}_{batch_size}_{eta_min}_{eta_max}_{ns}_{self.lamda}_{self.seed}.png')
        else:
            plt.savefig(
                f'History/{exp}_{metric}_{epochs}_{batch_size}_{eta}_{self.lamda}_{self.seed}.png')
        plt.show()

    @staticmethod
    def load_mlp(GDparams, cyclic=True, k=2, dims=[3072, 50, 10], lamda=0, seed=42, cycle=-1):
        mlp = MLP(k, dims, lamda, seed)
        if cyclic:
            n_cycles, batch_size, eta_min, eta_max, ns, exp = GDparams["n_cycles"], GDparams[
                "n_batch"], GDparams["eta_min"], GDparams["eta_max"], GDparams["ns"], GDparams["exp"]
            layers = np.load(
                f'History/{exp}_layers_{n_cycles}_{cycle}_{batch_size}_{eta_min}_{eta_max}_{ns}_{mlp.lamda}_{mlp.seed}.npy', allow_pickle=True)
            hist = np.load(
                f'History/{exp}_hist_{n_cycles}_{cycle}_{batch_size}_{eta_min}_{eta_max}_{ns}_{mlp.lamda}_{mlp.seed}.npy', allow_pickle=True)
        else:

            epochs, batch_size, eta, exp = GDparams["n_epochs"], GDparams[
                "n_batch"], GDparams["eta"], GDparams["exp"]

            layers = np.load(
                f'History/{exp}_layers_{epochs}_{batch_size}_{eta}_{mlp.lamda}_{mlp.seed}.npy', allow_pickle=True)

            hist = np.load(
                f'History/{exp}_hist_{epochs}_{batch_size}_{eta}_{mlp.lamda}_{mlp.seed}.npy', allow_pickle=True)

        mlp.layers = layers

        mlp.train_acc = hist.item()['train_acc']
        mlp.train_loss = hist.item()["train_loss"]
        mlp.train_cost = hist.item()["train_cost"]
        mlp.val_acc = hist.item()['val_acc']
        mlp.val_loss = hist.item()["val_loss"]
        mlp.val_cost = hist.item()["val_cost"]

        return mlp

    @staticmethod
    def majority_voting(X, y, GDparams, n_cycle=3, lamda=0.1):

        predictions = []
        for c in range(n_cycle):
            model = MLP.load_mlp(GDparams, cyclic=True, cycle=c, lamda=lamda)
            P = model.forward_pass(X)
            predictions.append(np.argmax(P, axis=0))
        predictions = np.array(predictions)
        majority_voting_class = [Counter(predictions[:, i]).most_common(1)[
            0][0] for i in range(X.shape[1])]
        return majority_voting_class, accuracy_score(y, majority_voting_class)

    def lr_range_test(self, data, GDparams, freq=20):

        X, Y, y, X_val, y_val = data["X_train"], data["Y_train"], data["y_train"], data["X_val"], data["y_val"],

        _, n = X.shape

        epochs, batch_size, eta_min, eta_max = GDparams["n_epochs"], GDparams[
            "n_batch"], GDparams["eta_min"],  GDparams["eta_max"]

        delta_eta = (eta_max - eta_min) / (n//batch_size * epochs) * freq
        eta = eta_min
        etas = [eta]

        v_acc = self.compute_accuracy(X_val, y_val)
        self.val_acc.append(v_acc)

        for epoch in tqdm(range(epochs)):

            X, Y, y = shuffle(X.T, Y.T, y.T, random_state=epoch)
            X, Y, y = X.T, Y.T, y.T

            for j in range(n//batch_size):
                j_start = j * batch_size
                j_end = (j+1) * batch_size
                X_batch = X[:, j_start:j_end]
                Y_batch = Y[:, j_start:j_end]

                P_batch = self.forward_pass(X_batch)

                self.compute_gradients(X_batch, Y_batch, P_batch)

                self.update_parameters(eta)
                if j % freq == 0:
                    eta += delta_eta
                    etas.append(eta)

                    v_acc = self.compute_accuracy(X_val, y_val)
                    self.val_acc.append(v_acc)

        return etas, self.val_acc

    @staticmethod
    def plot_accuracies(etas, accuracies, lamda, h, metric="Accuracy"):
        plt.plot(etas, accuracies)
        plt.xlabel("Learning Rate")
        plt.ylabel(metric)
        plt.title(f'{metric} vs learning rate - lamda={lamda} h={h}')
        plt.legend()
        plt.savefig(f'History/boundaries_{lamda}_{h}.png')
        plt.show()
    
    @staticmethod
    def random_jitter(X, flip=0, sigma=1):
        X_jitter = np.copy(X) 
        noise = np.random.normal(0, sigma, (X.shape))
        X_jitter += noise
        mean, std = np.mean(X_jitter, axis=1), np.std(X_jitter, axis = 1)
        X_jitter -= np.outer(mean, np.ones(X_jitter.shape[1]))
        X_jitter /= np.outer(std, np.ones(X.shape[1]))
        d, n_batch = X.shape
        if flip > 0.5:
            X_jitter = X_jitter.reshape(n_batch, 3, 32, 32).transpose(0, 2, 3, 1)
            X_jitter = np.array([np.fliplr(X_jitter[i]) for i in range(n_batch)])
            X_jitter = X_jitter.reshape((d, n_batch))
        return X_jitter

class Search():
    
    def __init__(self, l_min=-5, l_max=-1, n_lambda=20, sample=True, seed=42):
        np.random.seed(seed)
        self.l_min = l_min
        self.l_max = l_max
        self.n_lambda = n_lambda
        if sample:
            self.lambdas = self.sample_lambda()
        else: 
            self.lambdas = np.linspace(l_min, l_max, num=n_lambda)

    def sample_lambda(self):
        exp = self.l_min + (self.l_max - self.l_min) * \
            np.random.rand(self.n_lambda)
        lambdas = [10**e for e in exp]
        return lambdas

    def random_search(self, data, GDparams, lamdas=None):
        if lamdas is not None:
            self.lambdas = lamdas
        for lmda in self.lambdas:
            mlp = MLP(lamda=lmda)
            mlp.cyclic_learning(
                data, GDparams, verbose=False, backup=True)

    def random_search_perf(self, GDparams, lamdas=None):
        if lamdas is not None:
            self.lambdas = lamdas
        models = defaultdict(list)
        for lmda in self.lambdas:
            model = MLP.load_mlp(GDparams, cyclic=True, lamda=lmda)
            models[model.val_acc[-1]*100
                ].append({"lamda": round(lmda,7), "train_acc": round(model.train_acc[-1]*100, 5)})
        for acc in sorted(models.keys(), reverse=True):
            for v in models[acc]:
                print(f'{v["lamda"]} & {v["train_acc"]} & {round(acc,5)} \\\\')