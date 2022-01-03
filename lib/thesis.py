import pickle
import numpy as np
import functools
import fish_corr as fc
import matplotlib.pyplot as plt
import pickle
from scipy.interpolate import interp1d
from matplotlib import style
style.use('yushi')


class Dataset:
    def __init__(self):
        self.movies = []
        self.tanks = []
        self.__movie_files = []
        self.__tank_files = []
        self.cache = {}

    def add_movie(self, movie_fn, tank_fn):
        self.__movie_files.append(movie_fn)
        self.__tank_files.append(tank_fn)
        with open(tank_fn, 'rb') as f:
            self.tanks.append(pickle.load(f))
        with open(movie_fn, 'rb') as f:
            self.movies.append(pickle.load(f))

    def __iadd__(self, data):
        """
        add a new movie and tank

        Args:
            data (tuple): movie filename, tank filename
        """
        self.add_movie(*data)
        return self

    def __caching(name):
        """
        Decorator to store the results, avoid unnecessary & repeated calculation

        Args:
            name (str): the name of the quantity that will be stored in self.cache

        Example:
            @__caching("new_quantity")
            self.scan_new_quantity(arguments)
        """
        def decorator(method):
            @functools.wraps(method)
            def cached_method(self, *args, **kwargs):
                if name in self.cache:
                    return self.cache[name]
                else:
                    result = method(self, *args, **kwargs)
                    self.cache[name] = result
                    return result
            return cached_method
        return decorator

    @__caching('xyz')
    def __accumulate_xyz(self):
        """
        xyz shape : 3, n
        """
        x_vals, y_vals, z_vals = [], [], []
        for movie, tank in zip(self.movies, self.tanks):
            for frame in movie:
                x, y, z = frame.T - tank.base
                x_vals.append(x)
                y_vals.append(y)
                z_vals.append(z)
        x_vals = np.concatenate(x_vals)
        y_vals = np.concatenate(y_vals)
        z_vals = np.concatenate(z_vals)
        xyz = np.array((x_vals, y_vals, z_vals))
        return xyz

    def report_density(self, save_name, show=False, figsize=(12, 6)):
        self.__accumulate_xyz()

        x, y, z = self.cache['xyz']
        r = np.sqrt(x**2 + y**2)

        h = max([tank.z_max / 1000 for tank in self.tanks])
        c = 0.734
        r_max = np.sqrt(h / c)

        x_gas =  np.linspace(-r_max, r_max, 100)
        r_gas =  np.linspace(0, r_max, 100)
        z_gas =  np.linspace(0, h, 100)

        fx = (8 * c * np.sqrt(h / c - x_gas**2) * (h - c * x_gas**2)) / (3 * np.pi * h**2)
        fr = 4*c / h * r_gas - 4 * c**2 / h**2 * r_gas**3
        fz = 2 / h**2 * z_gas

        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(5, 3)
        ax_joint = fig.add_subplot(gs[:2, :-1])
        ax_legend = fig.add_subplot(gs[:2, -1])
        ax_x = fig.add_subplot(gs[2:, 0])
        ax_r = fig.add_subplot(gs[2:, 1])
        ax_z = fig.add_subplot(gs[2:, 2])

        hist_arg = {
            'color': 'whitesmoke', 'label': 'fish', 'density': True,
            'bins': 40, 'ec': 'k'
        }

        nbins = 26
        bin_y = np.linspace(-r_max, r_max, nbins * 2)
        bin_z = np.linspace(0, h, nbins)

        bc_y = (bin_y[1:] + bin_y[:-1]) / 2
        bc_z = (bin_z[1:] + bin_z[:-1]) / 2

        fv2i_x = lambda x : np.polyval(np.polyfit(bc_y, np.arange(len(bc_y)), deg=2), x)
        fv2i_y = lambda x : np.polyval(np.polyfit(bc_z, np.arange(len(bc_z)), deg=2), x)

        xtickvals = np.arange(-0.5, 0.7, 0.2)
        ytickvals = np.arange(0.0, 0.25, 0.1)

        xticks = list(map(fv2i_x, list(xtickvals)))
        yticks = list(map(fv2i_y, list(ytickvals)))

        ax_joint.set_xticks(xticks)
        ax_joint.set_xticklabels([f'{val:.2f}' for val in xtickvals])

        ax_joint.set_yticks(yticks)
        ax_joint.set_yticklabels([f'{val:.2f}' for val in ytickvals])

        tank_x = np.linspace(-r_max, r_max, 100)
        tank_z = c * tank_x ** 2
        water = np.ones(tank_x.shape) * h

        ax_joint.plot(fv2i_x(tank_x), fv2i_y(tank_z), color='k')

        hist, bin_y, bin_z = np.histogram2d(y/1000, z/1000, bins=(bin_y, bin_z))
        ax_joint.imshow(hist.T, aspect='auto', cmap='gray_r', vmin=0, vmax=hist.max() * 1.0)
        ax_joint.set_ylim(0, 20)
        ax_joint.set_xlabel("Y")
        ax_joint.set_ylabel("Z")


        ax_legend.hist([], **hist_arg)
        ax_legend.plot([], [], label='random', color='k', ls='--')
        ax_legend.plot([], [], label='tank', color='k')
        ax_legend.legend()
        ax_legend.axis('off')

        ax_x.hist(x / 1000, **hist_arg)
        ax_x.plot(x_gas, fx, label='random', color='k', ls='--')
        ax_x.set_xlim(-r_max, r_max)
        ax_x.set_xlabel("X / m")
        ax_x.set_ylabel("PDF")

        ax_r.hist(r / 1000, **hist_arg)
        ax_r.plot(r_gas, fr, label='random', color='k', ls='--')
        ax_r.set_xlim(0, r_max)
        ax_r.set_xlabel("R / m")
        ax_r.set_ylabel("PDF")

        ax_z.hist(z / 1000, **hist_arg)
        ax_z.plot(z_gas, fz, label='random', color='k', ls='--')
        ax_z.set_xlim(0, h)

        ax_z.set_xlabel("Z / m")
        ax_z.set_ylabel("PDF")

        plt.tight_layout()

        if show:
            plt.show()
        if save_name:
            plt.savefig(save_name)


    def save(self, filename):
        data = {
            'cache': self.cache,
            'movie_files': self.__movie_files,
            'tank_files': self.__tank_files,
        }
        with open(filename, 'wb') as f:
            pickle.dump(data, f)


    def read(self, filename):
        with open(filename, 'rb') as f:
            data = pickle.load(f)
        self.cache = data['cache']
        self.__movie_files = data['movie_files']
        self.__tank_files = data['tank_files']
        self.reload()

    def reload(self):
        self.movies, self.tanks = [], []
        for movie_fn, tank_fn in zip(self.__movie_files, self.__tank_files):
            with open(tank_fn, 'rb') as f:
                self.tanks.append(pickle.load(f))
            with open(movie_fn, 'rb') as f:
                self.movies.append(pickle.load(f))


class Dataset2D:
    def __init__(self):
        self.movies = []
        self.tanks = []
        self.__movie_files = []
        self.__tank_files = []
        self.cache = {}

    def add_movie(self, movie_fn, tank_fn):
        self.__movie_files.append(movie_fn)
        self.__tank_files.append(tank_fn)
        with open(tank_fn, 'rb') as f:
            self.tanks.append(pickle.load(f))
        with open(movie_fn, 'rb') as f:
            self.movies.append(pickle.load(f))

    def __iadd__(self, data):
        """
        add a new movie and tank

        Args:
            data (tuple): movie filename, tank filename
        """
        self.add_movie(*data)
        return self

    def __caching(name):
        """
        Decorator to store the results, avoid unnecessary & repeated calculation

        Args:
            name (str): the name of the quantity that will be stored in self.cache

        Example:
            @__caching("new_quantity")
            self.scan_new_quantity(arguments)
        """
        def decorator(method):
            @functools.wraps(method)
            def cached_method(self, *args, **kwargs):
                if name in self.cache:
                    return self.cache[name]
                else:
                    result = method(self, *args, **kwargs)
                    self.cache[name] = result
                    return result
            return cached_method
        return decorator

    @__caching('xy')
    def __accumulate_xy(self):
        """
        xy shape : 2, n
        """
        x_vals, y_vals = [], []
        for movie, tank in zip(self.movies, self.tanks):
            for frame in movie:
                x, y, z = frame.T - tank.base
                x_vals.append(x)
                y_vals.append(y)
                z_vals.append(z)
        x_vals = np.concatenate(x_vals)
        y_vals = np.concatenate(y_vals)
        z_vals = np.concatenate(z_vals)
        xyz = np.array((x_vals, y_vals, z_vals))
        return xyz

    def report_density(self, save_name, show=False, figsize=(12, 6)):
        self.__accumulate_xyz()

        x, y = self.cache['xy']
        r = np.sqrt(x**2 + y**2)

        h = max([tank.z_max / 1000 for tank in self.tanks])
        c = 0.734
        r_max = np.sqrt(h / c)

        x_gas =  np.linspace(-r_max, r_max, 100)
        r_gas =  np.linspace(0, r_max, 100)
        z_gas =  np.linspace(0, h, 100)

        fx = (8 * c * np.sqrt(h / c - x_gas**2) * (h - c * x_gas**2)) / (3 * np.pi * h**2)
        fr = 4*c / h * r_gas - 4 * c**2 / h**2 * r_gas**3
        fz = 2 / h**2 * z_gas

        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(5, 3)
        ax_joint = fig.add_subplot(gs[:2, :-1])
        ax_legend = fig.add_subplot(gs[:2, -1])
        ax_x = fig.add_subplot(gs[2:, 0])
        ax_r = fig.add_subplot(gs[2:, 1])
        ax_z = fig.add_subplot(gs[2:, 2])

        hist_arg = {
            'color': 'whitesmoke', 'label': 'fish', 'density': True,
            'bins': 40, 'ec': 'k'
        }

        nbins = 26
        bin_y = np.linspace(-r_max, r_max, nbins * 2)
        bin_z = np.linspace(0, h, nbins)

        bc_y = (bin_y[1:] + bin_y[:-1]) / 2
        bc_z = (bin_z[1:] + bin_z[:-1]) / 2

        fv2i_x = lambda x : np.polyval(np.polyfit(bc_y, np.arange(len(bc_y)), deg=2), x)
        fv2i_y = lambda x : np.polyval(np.polyfit(bc_z, np.arange(len(bc_z)), deg=2), x)

        xtickvals = np.arange(-0.5, 0.7, 0.2)
        ytickvals = np.arange(0.0, 0.25, 0.1)

        xticks = list(map(fv2i_x, list(xtickvals)))
        yticks = list(map(fv2i_y, list(ytickvals)))

        ax_joint.set_xticks(xticks)
        ax_joint.set_xticklabels([f'{val:.2f}' for val in xtickvals])

        ax_joint.set_yticks(yticks)
        ax_joint.set_yticklabels([f'{val:.2f}' for val in ytickvals])

        tank_x = np.linspace(-r_max, r_max, 100)
        tank_z = c * tank_x ** 2
        water = np.ones(tank_x.shape) * h

        ax_joint.plot(fv2i_x(tank_x), fv2i_y(tank_z), color='k')

        hist, bin_y, bin_z = np.histogram2d(y/1000, z/1000, bins=(bin_y, bin_z))
        ax_joint.imshow(hist.T, aspect='auto', cmap='gray_r', vmin=0, vmax=hist.max() * 1.0)
        ax_joint.set_ylim(0, 20)
        ax_joint.set_xlabel("Y")
        ax_joint.set_ylabel("Z")


        ax_legend.hist([], **hist_arg)
        ax_legend.plot([], [], label='random', color='k', ls='--')
        ax_legend.plot([], [], label='tank', color='k')
        ax_legend.legend()
        ax_legend.axis('off')

        ax_x.hist(x / 1000, **hist_arg)
        ax_x.plot(x_gas, fx, label='random', color='k', ls='--')
        ax_x.set_xlim(-r_max, r_max)
        ax_x.set_xlabel("X / m")
        ax_x.set_ylabel("PDF")

        ax_r.hist(r / 1000, **hist_arg)
        ax_r.plot(r_gas, fr, label='random', color='k', ls='--')
        ax_r.set_xlim(0, r_max)
        ax_r.set_xlabel("R / m")
        ax_r.set_ylabel("PDF")

        ax_z.hist(z / 1000, **hist_arg)
        ax_z.plot(z_gas, fz, label='random', color='k', ls='--')
        ax_z.set_xlim(0, h)

        ax_z.set_xlabel("Z / m")
        ax_z.set_ylabel("PDF")

        plt.tight_layout()

        if show:
            plt.show()
        if save_name:
            plt.savefig(save_name)


    def save(self, filename):
        data = {
            'cache': self.cache,
            'movie_files': self.__movie_files,
            'tank_files': self.__tank_files,
        }
        with open(filename, 'wb') as f:
            pickle.dump(data, f)


    def read(self, filename):
        with open(filename, 'rb') as f:
            data = pickle.load(f)
        self.cache = data['cache']
        self.__movie_files = data['movie_files']
        self.__tank_files = data['tank_files']
        self.reload()


    def reload(self):
        self.movies, self.tanks = [], []
        for movie_fn, tank_fn in zip(self.__movie_files, self.__tank_files):
            with open(tank_fn, 'rb') as f:
                self.tanks.append(pickle.load(f))
            with open(movie_fn, 'rb') as f:
                self.movies.append(pickle.load(f))
