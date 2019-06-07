""" Various utilities.
"""
import random
from argparse import Namespace

import gym
import torch
from gym_minigrid.wrappers import ImgObsWrapper
from termcolor import colored as clr

import rlog
from wintermute.env_wrappers import FrameStack


class TorchWrapper(gym.ObservationWrapper):
    """ From numpy to torch. """

    def __init__(self, env, device, verbose=False):
        super().__init__(env)
        self.device = device
        self.max_ratio = int(255 / 9)

        if verbose:
            print("[Torch Wrapper] for returning PyTorch Tensors.")

    def observation(self, obs):
        """ Convert from numpy to torch.
            Also change from (h, w, c*hist) to (batch, hist*c, h, w)
        """
        # obs = torch.from_numpy(obs).permute(0, 3, 1, 2).unsqueeze(0)
        obs = torch.from_numpy(obs)
        obs = obs.permute(2, 1, 0)

        # [hist_len * channels, w, h] -> [1, hist_len, channels, w, h]
        # we are always using RGB
        obs = obs.view(int(obs.shape[0] / 3), 3, 7, 7).unsqueeze(0)

        # scale the symbolic representention from [0,9] to [0, 255]
        obs = obs.mul_(self.max_ratio).byte()
        return obs.to(self.device)


def wrap_env(env, opt):
    env = ImgObsWrapper(env)
    env = FrameStack(env, k=opt.hist_len)
    env = TorchWrapper(env, device=opt.device)
    return env


def augment_options(opt):
    if "experiment" not in opt.__dict__:
        opt.experiment = f"{''.join(opt.game.split('-')[1:-1])}-DQN"
    if opt.subset:
        opt.subset = [random.randint(0, 10000) for _ in range(opt.subset)]
    opt.device = torch.device(opt.device)
    return opt


def configure_logger(opt):
    rlog.init(opt.experiment, path=opt.out_dir)
    train_log = rlog.getLogger(opt.experiment + ".train")
    train_log.addMetrics(
        [
            rlog.AvgMetric("R/ep", metargs=["reward", "done"]),
            rlog.SumMetric("ep_cnt", resetable=False, metargs=["done"]),
            rlog.AvgMetric("steps/ep", metargs=["step_no", "done"]),
            rlog.FPSMetric("learning_fps", metargs=["frame_no"]),
        ]
    )
    test_log = rlog.getLogger(opt.experiment + ".test")
    test_log.addMetrics(
        [
            rlog.AvgMetric("R/ep", metargs=["reward", "done"]),
            rlog.SumMetric("ep_cnt", resetable=False, metargs=["done"]),
            rlog.AvgMetric("steps/ep", metargs=["frame_no", "done"]),
            rlog.FPSMetric("test_fps", metargs=["frame_no"]),
            rlog.MaxMetric("max_q", metargs=["qval"]),
        ]
    )


def config_to_string(
    cfg: Namespace, indent: int = 0, color: bool = True
) -> str:
    """Creates a multi-line string with the contents of @cfg."""

    text = ""
    for key, value in cfg.__dict__.items():
        ckey = clr(key, "yellow", attrs=["bold"]) if color else key
        text += " " * indent + ckey + ": "
        if isinstance(value, Namespace):
            text += "\n" + config_to_string(value, indent + 2, color=color)
        else:
            cvalue = clr(str(value), "white") if color else str(value)
            text += cvalue + "\n"
    return text
