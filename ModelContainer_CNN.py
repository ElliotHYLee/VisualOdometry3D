import torch.optim as optim
from VODataSet import DataLoader
import torch
import torch.nn as nn
import sys
import numpy as np
from MyPyTorchAPI.CustomLoss import MahalanobisLoss
from tkinter import *

class ModelContainer_CNN():
    def __init__(self, net_model):
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        print(torch.cuda.device)
        self.model = nn.DataParallel(net_model).to(self.device)
        self.compile()
        self.train_loss = []
        self.val_loss = []
        self.wName = None
        self.current_val_loss = 10**5
        self.min_val_loss = 10**5

        master = Tk()
        Label(master, text="lRate").grid(row=0)
        Label(master, text="wDecay").grid(row=1)

        e1 = Entry(master)
        e2 = Entry(master)

        e1.grid(row=0, column=1)
        e2.grid(row=1, column=1)

        #Button(master, text='Quit', command=master.quit).grid(row=3, column=0, sticky=W, pady=4)
        Button(master, text='Update', command=self.updateLearningRate).grid(row=3, column=1, sticky=W, pady=4)
        mainloop()

    def updateLearningRate(self):
        lr = el.get()
        self.optimizer = optim.RMSprop(self.model.parameters(), lr=lr, weight_decay=10 ** -4)
        print('current lr = %f'%(lr))

    def compile(self, loss=None, optimizer=None):
        self.loss = MahalanobisLoss()#nn.modules.loss.L1Loss()
        # self.optimizer = optim.SGD(self.model.parameters(), lr=10**-2, weight_decay=0.01)
        self.optimizer = optim.RMSprop(self.model.parameters(), lr=10**-4, weight_decay=10**-4)

    def fit(self, train, validation=None, batch_size=1, epochs=1, shuffle=True, wName='weight.pt', checkPointFreq = 1):
        self.checkPointFreq = checkPointFreq
        self.wName = wName if self.wName is None else self.wName
        self.train_loader = DataLoader(dataset=train, batch_size=batch_size, shuffle=shuffle)
        self.valid_loader = DataLoader(dataset=validation, batch_size=batch_size, shuffle=shuffle)

        for epoch in range(0, epochs):
            train_loss, val_loss = self.runEpoch(epoch)
            self.current_val_loss = val_loss
            self.train_loss.append(train_loss)
            self.val_loss.append(val_loss)
            # save weighs
            if np.mod(epoch, self.checkPointFreq)==0:
                self.save_weights(self.wName)

    def checkIfMinVal(self):
        if self.min_val_loss >= self.current_val_loss:
            self.min_val_loss = self.current_val_loss
            return True
        else:
            return False

    def save_weights(self, fName):
        if self.checkIfMinVal():
            fName = fName + '_best'
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'train_loss': self.train_loss,
            'val_loss': self.val_loss,
        }, fName + '.pt')

    def load_weights(self, path, train = True):
        self.wName = path + '.pt'
        checkPoint = torch.load(path + '.pt')
        self.model.load_state_dict(checkPoint['model_state_dict'])
        self.optimizer.load_state_dict(checkPoint['optimizer_state_dict'])
        self.train_loss = checkPoint['train_loss']
        self.val_loss = checkPoint['val_loss']
        self.min_val_loss = np.min(self.val_loss)
        if train:
            self.model.train()
        else:
            self.model.eval()

    def getLossHistory(self):
        return np.array(self.train_loss), np.array(self.val_loss)

    def runEpoch(self, epoch):
        epoch_loss = 0
        self.model.train(True)
        for batch_idx, (img0, img1, du, dw, dtrans) in enumerate(self.train_loader):
            img0 = img0.to(self.device)
            img1 = img1.to(self.device)
            du = du.to(self.device)
            dw = dw.to(self.device)
            dtrans = dtrans.to(self.device)

            # forward pass and calc loss
            pr_du, pr_dw, pr_du_cov, pr_dw_cov, pr_dtrans = self.model(img0, img1)
            batch_loss = self.loss(pr_du, du, pr_du_cov) + self.loss(pr_dw, dw, pr_dw_cov)
            epoch_loss += batch_loss.item()

            # update weights
            self.optimizer.zero_grad()
            batch_loss.backward()
            self.optimizer.step()

            # output msg
            self.print_batch_result(epoch, batch_idx, len(self.train_loader), batch_loss.item())

        ## calc train and validation losses
        val_loss = self.validate()
        train_loss = epoch_loss / len(self.train_loader)
        self.print_epoch_result(epoch, train_loss, val_loss)
        return train_loss, val_loss

    def print_epoch_result(self, epoch, train_loss, val_loss):
        msg = "===> Epoch {} Complete. Avg-Loss => Train: {:.4f} Validation: {:.4f}".format(epoch, train_loss, val_loss)
        sys.stdout.write('\r' + msg)
        print('')

    def print_batch_result(self, epoch, batch_idx, N, loss):
        msg = "===> Epoch[{}]({}/{}): Batch Loss: {:.4f}".format(epoch, batch_idx, N, loss)
        sys.stdout.write('\r' + msg)

    def validate(self):
        self.model.eval()
        loss = self.predict(self.valid_loader, isValidation=True)
        return loss

    def predict(self, data_incoming, isValidation=False, isTarget=True):
        data_loader = data_incoming if isValidation else DataLoader(dataset=data_incoming, batch_size=16, shuffle=False)
        du_list, dw_list, du_cov_list, dw_cov_list, dtrans_list = [], [], [], [], []
        loss = 0
        for batch_idx, (img0, img1, du, dw, dtrans) in enumerate(data_loader):
            img0 = img0.to(self.device)
            img1 = img1.to(self.device)
            du = du.to(self.device)
            dw = dw.to(self.device)
            dtrans = dtrans.to(self.device)

            with torch.no_grad():
                pr_du, pr_dw, pr_du_cov, pr_dw_cov, pr_dtrans = self.model(img0, img1)
                if not isValidation:
                    du_list.append(pr_du.cpu().data.numpy())
                    dw_list.append(pr_dw.cpu().data.numpy())
                    du_cov_list.append(pr_du_cov.cpu().data.numpy())
                    dw_cov_list.append(pr_dw_cov.cpu().data.numpy())
                    #dtrans_list.append(pr_dtrans.cpu().data.numpy())
                if isTarget:
                    du = du.to(self.device)
                    batch_loss = self.loss(pr_du, du, pr_du_cov) + self.loss(pr_dw, dw, pr_dw_cov)
                    loss += batch_loss.item()

        mae = loss / len(data_loader)
        if isValidation:
            return mae
        else:
            pr_du = np.concatenate(du_list, axis=0)
            pr_dw = np.concatenate(dw_list, axis=0)
            du_cov = np.concatenate(du_cov_list, axis=0)
            dw_cov = np.concatenate(dw_cov_list, axis=0)
            dtrans =None#np.concatenate(dtrans_list, axis=0)
            return pr_du, pr_dw, du_cov, dw_cov, dtrans, mae

if __name__ == '__main__':
    # from Model_CNN_0 import Model_CNN_0
    # mc = ModelContainer_CNN(Model_CNN_0())
    from tkinter import *


    def show_entry_fields():
        print("First Name: %s\nLast Name: %s" % (e1.get(), e2.get()))


    master = Tk()
    Label(master, text="First Name").grid(row=0)
    Label(master, text="Last Name").grid(row=1)

    e1 = Entry(master)
    e2 = Entry(master)

    e1.grid(row=0, column=1)
    e2.grid(row=1, column=1)

    Button(master, text='Quit', command=master.quit).grid(row=3, column=0, sticky=W, pady=4)
    Button(master, text='Show', command=show_entry_fields).grid(row=3, column=1, sticky=W, pady=4)

    mainloop()
