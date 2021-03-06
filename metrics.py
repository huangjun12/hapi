# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import six
import abc
import numpy as np
import paddle.fluid as fluid

import logging
FORMAT = '%(asctime)s-%(levelname)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

__all__ = ['Metric', 'Accuracy']


@six.add_metaclass(abc.ABCMeta)
class Metric(object):
    """
    Base class for metric, encapsulates metric logic and APIs

    Usage:
    m = SomeMetric()
    for prediction, label in ...:
        m.update(prediction, label)
    m.accumulate()
    """

    @abc.abstractmethod
    def reset(self):
        """
        Reset states and result
        """
        raise NotImplementedError("function 'reset' not implemented in {}.".
                                  format(self.__class__.__name__))

    @abc.abstractmethod
    def update(self, *args, **kwargs):
        """
        Update states for metric
        """
        raise NotImplementedError("function 'update' not implemented in {}.".
                                  format(self.__class__.__name__))

    @abc.abstractmethod
    def accumulate(self):
        """
        Accumulates statistics, computes and returns the metric value
        """
        raise NotImplementedError(
            "function 'accumulate' not implemented in {}.".format(
                self.__class__.__name__))

    @abc.abstractmethod
    def name(self):
        """
        Returns metric name
        """
        raise NotImplementedError("function 'name' not implemented in {}.".
                                  format(self.__class__.__name__))

    def add_metric_op(self, pred, label):
        """
        Add process op for metric in program
        """
        return pred, label


class Accuracy(Metric):
    """
    Encapsulates accuracy metric logic
    """

    def __init__(self, topk=(1, ), name=None, *args, **kwargs):
        super(Accuracy, self).__init__(*args, **kwargs)
        self.topk = topk
        self.maxk = max(topk)
        self._init_name(name)
        self.reset()

    def add_metric_op(self, pred, label, *args, **kwargs):
        pred = fluid.layers.argsort(pred[0], descending=True)[1][:, :self.maxk]
        correct = pred == label[0]
        return correct

    def update(self, correct, *args, **kwargs):
        accs = []
        for i, k in enumerate(self.topk):
            num_corrects = correct[:, :k].sum()
            num_samples = len(correct)
            accs.append(float(num_corrects) / num_samples)
            self.total[i] += num_corrects
            self.count[i] += num_samples
        return accs

    def reset(self):
        self.total = [0.] * len(self.topk)
        self.count = [0] * len(self.topk)

    def accumulate(self):
        res = []
        for t, c in zip(self.total, self.count):
            res.append(float(t) / c)
        return res

    def _init_name(self, name):
        name = name or 'acc'
        if self.maxk != 1:
            self._name = ['{}_top{}'.format(name, k) for k in self.topk]
        else:
            self._name = ['acc']

    def name(self):
        return self._name
