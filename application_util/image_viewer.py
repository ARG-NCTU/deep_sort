# vim: expandtab:ts=4:sw=4
"""
This module contains an image viewer and drawing routines based on OpenCV.
"""
import numpy as np
import cv2
import time


def is_in_bounds(mat, roi):
    """Check if ROI is fully contained in the image.

    Parameters
    ----------
    mat : ndarray
        An ndarray of ndim>=2.
    roi : (int, int, int, int)
        Region of interest (x, y, width, height) where (x, y) is the top-left
        corner.

    Returns
    -------
    bool
        Returns true if the ROI is contain in mat.

    """
    if roi[0] < 0 or roi[0] + roi[2] >= mat.shape[1]:
        return False
    if roi[1] < 0 or roi[1] + roi[3] >= mat.shape[0]:
        return False
    return True


def view_roi(mat, roi):
    """Get sub-array.

    The ROI must be valid, i.e., fully contained in the image.

    Parameters
    ----------
    mat : ndarray
        An ndarray of ndim=2 or ndim=3.
    roi : (int, int, int, int)
        Region of interest (x, y, width, height) where (x, y) is the top-left
        corner.

    Returns
    -------
    ndarray
        A view of the roi.

    """
    sx, ex = roi[0], roi[0] + roi[2]
    sy, ey = roi[1], roi[1] + roi[3]
    if mat.ndim == 2:
        return mat[sy:ey, sx:ex]
    else:
        return mat[sy:ey, sx:ex, :]


class ImageViewer(object):
    """An image viewer with drawing routines and video capture capabilities.

    Key Bindings:

    * 'SPACE' : pause
    * 'ESC' : quit

    Parameters
    ----------
    update_ms : int
        Number of milliseconds between frames (1000 / frames per second).
    window_shape : (int, int)
        Shape of the window (width, height).
    caption : Optional[str]
        Title of the window.

    Attributes
    ----------
    image : ndarray
        Color image of shape (height, width, 3). You may directly manipulate
        this image to change the view. Otherwise, you may call any of the
        drawing routines of this class. Internally, the image is treated as
        beeing in BGR color space.

        Note that the image is resized to the the image viewers window_shape
        just prior to visualization. Therefore, you may pass differently sized
        images and call drawing routines with the appropriate, original point
        coordinates.
    color : (int, int, int)
        Current BGR color code that applies to all drawing routines.
        Values are in range [0-255].
    text_color : (int, int, int)
        Current BGR text color code that applies to all text rendering
        routines. Values are in range [0-255].
    thickness : int
        Stroke width in pixels that applies to all drawing routines.

    """

    def __init__(self, update_ms, window_shape=(640, 480), caption="Figure 1"):
        self._window_shape = window_shape
        self._caption = caption
        self._update_ms = update_ms
        self._video_writer = None
        self._user_fun = lambda: None
        self._terminate = False

        self.image = np.zeros(self._window_shape + (3, ), dtype=np.uint8)
        self._color = (0, 0, 0)
        self.text_color = (255, 255, 255)
        self.thickness = 1

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        if len(value) != 3:
            raise ValueError("color must be tuple of 3")
        self._color = tuple(int(c) for c in value)

    def rectangle(self, x, y, w, h, label=None):
        """Draw a rectangle.

        Parameters
        ----------
        x : float | int
            Top left corner of the rectangle (x-axis).
        y : float | int
            Top let corner of the rectangle (y-axis).
        w : float | int
            Width of the rectangle.
        h : float | int
            Height of the rectangle.
        label : Optional[str]
            A text label that is placed at the top left corner of the
            rectangle.

        """
        pt1 = int(x), int(y)
        pt2 = int(x + w), int(y + h)
        cv2.rectangle(self.image, pt1, pt2, self._color, self.thickness)
        if label is not None:
            text_size = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_PLAIN, 1, self.thickness)

            center = pt1[0] + 5, pt1[1] + 5 + text_size[0][1]
            pt2 = pt1[0] + 10 + text_size[0][0], pt1[1] + 10 + \
                text_size[0][1]
            cv2.rectangle(self.image, pt1, pt2, self._color, -1)
            cv2.putText(self.image, label, center, cv2.FONT_HERSHEY_PLAIN,
                        1, (255, 255, 255), self.thickness)

    def circle(self, x, y, radius, label=None):
        """Draw a circle.

        Parameters
        ----------
        x : float | int
            Center of the circle (x-axis).
        y : float | int
            Center of the circle (y-axis).
        radius : float | int
            Radius of the circle in pixels.
        label : Optional[str]
            A text label that is placed at the center of the circle.

        """
        image_size = int(radius + self.thickness + 1.5)  # actually half size
        roi = int(x - image_size), int(y - image_size), \
            int(2 * image_size), int(2 * image_size)
        if not is_in_bounds(self.image, roi):
            return

        image = view_roi(self.image, roi)
        center = image.shape[1] // 2, image.shape[0] // 2
        cv2.circle(
            image, center, int(radius + .5), self._color, self.thickness)
        if label is not None:
            cv2.putText(
                self.image, label, center, cv2.FONT_HERSHEY_PLAIN,
                2, self.text_color, 2)

    def gaussian(self, mean, covariance, label=None):
        """Draw 95% confidence ellipse of a 2-D Gaussian distribution.

        Parameters
        ----------
        mean : array_like
            The mean vector of the Gaussian distribution (ndim=1).
        covariance : array_like
            The 2x2 covariance matrix of the Gaussian distribution.
        label : Optional[str]
            A text label that is placed at the center of the ellipse.

        """
        # chi2inv(0.95, 2) = 5.9915
        vals, vecs = np.linalg.eigh(5.9915 * covariance)
        indices = vals.argsort()[::-1]
        vals, vecs = np.sqrt(vals[indices]), vecs[:, indices]

        center = int(mean[0] + .5), int(mean[1] + .5)
        axes = int(vals[0] + .5), int(vals[1] + .5)
        angle = int(180. * np.arctan2(vecs[1, 0], vecs[0, 0]) / np.pi)
        cv2.ellipse(
            self.image, center, axes, angle, 0, 360, self._color, 2)
        if label is not None:
            cv2.putText(self.image, label, center, cv2.FONT_HERSHEY_PLAIN,
                        2, self.text_color, 2)

    def annotate(self, x, y, text):
        """Draws a text string at a given location.

        Parameters
        ----------
        x : int | float
            Bottom-left corner of the text in the image (x-axis).
        y : int | float
            Bottom-left corner of the text in the image (y-axis).
        text : str
            The text to be drawn.

        """
        cv2.putText(self.image, text, (int(x), int(y)), cv2.FONT_HERSHEY_PLAIN,
                    2, self.text_color, 2)

    def colored_points(self, points, colors=None, skip_index_check=False):
        """Draw a collection of points.

        The point size is fixed to 1.

        Parameters
        ----------
        points : ndarray
            The Nx2 array of image locations, where the first dimension is
            the x-coordinate and the second dimension is the y-coordinate.
        colors : Optional[ndarray]
            The Nx3 array of colors (dtype=np.uint8). If None, the current
            color attribute is used.
        skip_index_check : Optional[bool]
            If True, index range checks are skipped. This is faster, but
            requires all points to lie within the image dimensions.

        """
        if not skip_index_check:
            cond1, cond2 = points[:, 0] >= 0, points[:, 0] < 480
            cond3, cond4 = points[:, 1] >= 0, points[:, 1] < 640
            indices = np.logical_and.reduce((cond1, cond2, cond3, cond4))
            points = points[indices, :]
        if colors is None:
            colors = np.repeat(
                self._color, len(points)).reshape(3, len(points)).T
        indices = (points + .5).astype(np.int64)
        self.image[indices[:, 1], indices[:, 0], :] = colors

    def enable_videowriter(self, output_filename, fourcc_string="MJPG",
                           fps=None):
        """ Write images to video file.

        Parameters
        ----------
        output_filename : str
            Output filename.
        fourcc_string : str
            The OpenCV FOURCC code that defines the video codec (check OpenCV
            documentation for more information).
        fps : Optional[float]
            Frames per second. If None, configured according to current
            parameters.

        """
        fourcc = cv2.VideoWriter_fourcc(*fourcc_string)
        if fps is None:
            fps = int(1000. / self._update_ms)
        self._video_writer = cv2.VideoWriter(
            output_filename, fourcc, fps, self._window_shape)

    def disable_videowriter(self):
        """ Disable writing videos.
        """
        self._video_writer = None

    def run(self, update_fun=None):
        """
        Start the image viewer, modified to save images instead of showing GUI.
        """
        if update_fun is not None:
            self._user_fun = update_fun

        self._terminate, is_paused = False, False
        frame_idx = 0   # ✅ 新增：frame index，用來命名輸出的圖片

        import os
        os.makedirs("output_frames", exist_ok=True)  # ✅ 新增：建立資料夾

        print("ImageViewer running in headless mode, saving frames to ./output_frames/")

        while not self._terminate:
            t0 = time.time()
            if not is_paused:
                self._terminate = not self._user_fun()
                if self._video_writer is not None:
                    self._video_writer.write(
                        cv2.resize(self.image, self._window_shape))
                # ✅ 新增：每個 frame 輸出成檔案
                filename = f"output_frames/frame_{frame_idx:05d}.jpg"
                resized = cv2.resize(self.image, self._window_shape[:2])
                cv2.imwrite(filename, resized)
                frame_idx += 1

            t1 = time.time()
            remaining_time = max(1, int(self._update_ms - 1e3*(t1 - t0)))
            # ❌ 移除 cv2.imshow 和 waitKey
            # cv2.imshow(...)
            # key = cv2.waitKey(remaining_time)

            # 改用 sleep 模擬原本更新間隔
            time.sleep(remaining_time / 1000.0)

        if self._video_writer is not None:
            self._video_writer.release()

        print("Viewer stopped, all frames saved.")


    def stop(self):
        """Stop the control loop.

        After calling this method, the viewer will stop execution before the
        next frame and hand over control flow to the user.

        Parameters
        ----------

        """
        self._terminate = True
