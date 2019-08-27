from src.DataReader.KF_DataUtils import *
import matplotlib.pyplot as plt
import numpy as np
from src.Params import getNoiseLevel
class ReadData():
    def __init__(self, dsName='airsim', subType='mr', seq=0):
        self.dsName = dsName
        self.subType = subType
        self.gt_path = getPath(dsName, seq=seq, subType=subType)

        # ground truth data
        self.gt_dt = pd.read_csv(self.gt_path + 'dt.txt', sep=',', header=None).values.astype(np.float32)
        self.gt_du = pd.read_csv(self.gt_path + 'du.txt', sep=',', header=None).values.astype(np.float32)
        self.gt_dw = pd.read_csv(self.gt_path + 'dw.txt', sep=',', header=None).values.astype(np.float32)
        self.gt_dtr = pd.read_csv(self.gt_path + 'dtrans.txt', sep=',', header=None).values.astype(np.float32)
        self.gt_dtr_gnd = pd.read_csv(self.gt_path + 'dtrans_gnd.txt', sep=',', header=None).values.astype(np.float32)
        self.gt_linR = pd.read_csv(self.gt_path + 'linR.txt', sep=',', header=None).values.astype(np.float32)
        self.gt_rotM_b2g = np.zeros((self.gt_linR.shape[0], 3, 3), dtype=np.float32)
        for i in range(0, self.gt_linR.shape[0]):
            self.gt_rotM_b2g[i, :, :] = np.reshape(self.gt_linR[i, :], (3, 3))
        self.pos_gnd = pd.read_csv(self.gt_path + 'pos.txt', sep=',', header=None).values.astype(np.float32)
        self.acc_gnd = pd.read_csv(self.gt_path + 'acc_gnd.txt', sep=',', header=None).values.astype(np.float32)
        self.gt_acc_gnd = pd.read_csv(self.gt_path + 'gt_acc_gnd.txt', sep=',', header=None).values.astype(np.float32)
        self.accdt_gnd = np.multiply(self.acc_gnd, self.gt_dt)
        self.gt_accdt_gnd = np.multiply(self.gt_acc_gnd, self.gt_dt)
        self.numData = self.gt_du.shape[0]
        # cnn outputs
        noise = getNoiseLevel()
        self.pr_path = getPrPath(dsName, seq, subType)
        self.pr_dtr_gnd = pd.read_csv(self.pr_path + '_dtr_gnd' + str(noise) + '.txt', sep=' ', header=None).values.astype(np.float32)
        self.pr_dtr_chol = pd.read_csv(self.pr_path + '_dtr_cov' + str(noise) + '.txt', sep=' ', header=None).values.astype(np.float32)

        # make cov_matrix
        index = 0
        self.pr_dtr_cov = np.zeros((self.numData, 3, 3), dtype=np.float32)
        L = np.zeros((self.numData, 3, 3))
        LT = np.zeros_like(L)
        for j in range(0, 3):
            for i in range(0, j + 1):
                L[:, j, i] = self.pr_dtr_chol[:, index]
                LT[:, i, j] = self.pr_dtr_chol[:, index]
                index += 1
        self.pr_dtr_cov = np.matmul(L, LT)
        self.pr_dtr_cov_gnd = np.matmul(self.gt_rotM_b2g, self.pr_dtr_cov)
        self.pr_dtr_cov_gnd = np.matmul(self.pr_dtr_cov_gnd, np.transpose(self.pr_dtr_cov_gnd, (0,2,1)))

        self.pr_dtr_std_gnd = np.zeros((self.numData, 3))
        for i in range(0, self.numData):
            self.pr_dtr_std_gnd[i,:] = np.sqrt(np.diag(self.pr_dtr_cov_gnd[i,:]))

        # print(self.numData)
        # print(self.gt_dtr_gnd.shape)
        # print(self.acc_gnd.shape)
        # print(self.gt_du.shape)
        # print(self.pr_dtr_gnd.shape)
        # print(self.pr_dtr_cov.shape)
        # print(self.pr_dtr_cov_gnd.shape)

if __name__ == '__main__':
    d = ReadData(dsName='airsim', subType='mr', seq=0)
    print(d.accdt_gnd.shape)
    print(d.gt_dt.shape)
    # vel_imu = np.zeros((d.gt_dt.shape[0]+1, 3))
    # for i in range(0, d.gt_dt.shape[0]):
    #     vel_imu[i+1] = vel_imu[i] + d.gt_dt[i]*d.acc_gnd[i,:]
    dummy = d.gt_dt * d.accdt_gnd
    print(dummy.shape)
    vel_imu = np.cumsum(dummy, axis=0)
    vel_imu = vel_imu[1:]

    print(vel_imu.shape)

    plt.figure()
    plt.subplot(311)
    plt.plot(d.gt_dtr_gnd[:,0], 'r.', markersize=5)
    plt.plot(d.pr_dtr_gnd[:, 0], 'b.', markersize=2)
    plt.plot(vel_imu[:, 0], 'g.', markersize=1)

    plt.subplot(312)
    plt.plot(d.gt_dtr_gnd[:, 1], 'r.', markersize=5)
    plt.plot(d.pr_dtr_gnd[:, 1], 'b.', markersize=2)
    plt.plot(vel_imu[:, 1], 'g.', markersize=1)

    plt.subplot(313)
    plt.plot(d.gt_dtr_gnd[:, 2], 'r.', markersize=5)
    plt.plot(d.pr_dtr_gnd[:, 2], 'b.', markersize=2)
    plt.plot(vel_imu[:, 2], 'g.', markersize=1)

    plt.figure()
    plt.subplot(311)
    plt.plot(d.gt_accdt_gnd[:, 0], 'r.-', markersize=5)
    plt.plot(d.accdt_gnd[:, 0], 'b.-', markersize=1)
    plt.subplot(312)
    plt.plot(d.gt_accdt_gnd[:, 1], 'r.-', markersize=5)
    plt.plot(d.accdt_gnd[:, 1], 'b.-', markersize=1)
    plt.subplot(313)
    plt.plot(d.gt_accdt_gnd[:, 2], 'r.-', markersize=5)
    plt.plot(d.accdt_gnd[:, 2], 'b.-', markersize=1)

    plt.show()