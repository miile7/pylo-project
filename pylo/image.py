import os
import json
import typing
import numpy as np

from PIL import Image as PILImage

from .exception_thread import ExceptionThread

# from .config import PROGRAM_NAME
# from .config import TIFF_IMAGE_TAGS_INDEX

def _export_image_object_to_jpg(file_path: str, image: "Image") -> None:
    """Save the given image object to the given file_path as a JPG file.

    The if the file already exists, it will be overwritten silently. If the 
    parent directory doesn't exist, or any error occurres, an Exception will be
    raised.

    Note that this function does not save the tags!

    Parameters:
    -----------
    file_path : str
        The path of the file to save to including the file name and the
        extension, if the path already exists, it will silently be 
        overwritten
    image : Image
        The image object to save
    """

    # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.fromarray,
    # mode defines whether RGB, RGBA, Grayscale, ... is used
    save_img = PILImage.fromarray(image.image_data, mode="L")
    save_img.save(file_path, format="jpeg", quality=100, optimize=False)

def _export_image_object_to_tiff(file_path: str, image: "Image") -> None:
    """Save the given image object to the given file_path as a TIFF file.

    The if the file already exists, it will be overwritten silently. If the 
    parent directory doesn't exist, or any error occurres, an Exception will be
    raised.

    Parameters:
    -----------
    file_path : str
        The path of the file to save to including the file name and the
        extension, if the path already exists, it will silently be 
        overwritten
    image : Image
        The image object to save
    """

    # import as late as possible to allow changes by extensions
    from .config import PROGRAM_NAME
    from .config import TIFF_IMAGE_TAGS_INDEX

    # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.fromarray,
    # mode defines whether RGB, RGBA, Grayscale, ... is used
    save_img = PILImage.fromarray(image.image_data, mode="L")
    save_img.save(file_path, format="tiff", 
                  # write tags as image description
                  tiffinfo={TIFF_IMAGE_TAGS_INDEX: json.dumps(image.tags)}, 
                  compression="raw", software=PROGRAM_NAME)

class Image:
    """This class represents an image.

    Attributes
    ----------
    image_data : numpy.array_like
        The illumination data of the image, this has to be a 2d array with 
        integer values between [0..255], so gray scale only is supported
    tags : dict
        Any tags that are related to this image, usually they contain the 
        acquision circumstances
    export_extensions : dict
        A dict that contains the file extension (without dot) as the key and a 
        callback as the value which is used for exporting the image to a file, 
        the callback takes two arguments where the first one is a valid path 
        (that should be overwritten if necessary), the second is the Image 
        object
    """
    export_extensions = {
        "jpg": _export_image_object_to_jpg,
        "jpeg": _export_image_object_to_jpg,
        "tif": _export_image_object_to_tiff,
        "tiff": _export_image_object_to_tiff
    }

    def __init__(self, image_data: typing.Any, tags: typing.Optional[dict]={}) -> None:
        """Create an image.
        
        Parameters
        ----------
        image_data : numpy.array_like
            The illumination data of the image, this has to be a 2d array with 
            integer values between [0..255], so gray scale only is supported
        tags : dict, optional
            Any tags that are related to this image, usually they contain the 
            acquision circumstances
        """

        self.image_data = np.array(image_data, dtype=np.uint8)
        self.tags = tags
    
    def _executeSave(self, file_type: str, file_path: str) -> None:
        """Execute the save.

        Raises
        ------
        ValueError
            When the file_type is not supported

        Parameters
        ----------
        file_type : str
            The file type, this is the extension that defines the save type in
            lower case only
        file_path : str
            The file path to save the image to (including the extension), 
            existing files will be silently overwritten
        """

        if (file_type in self.export_extensions and 
            callable(self.export_extensions[file_type])):
            self.export_extensions[file_type](file_path, self)
        else:
            raise ValueError(
                "The file extension {} is not supported.".format(file_type)
            )
        
    
    def saveTo(self, file_path: str, overwrite: typing.Optional[bool]=True, 
               create_directories: typing.Optional[bool]=False, 
               file_type: typing.Optional[str]=None) -> ExceptionThread:
        """Save the image to the given file_path.

        Note that the saving is done in another thread. The thread will be 
        started and then returned.

        Raises
        ------
        FileNotFoundError
            When create_directories is False and the directories do not exist
        FileExistsError
            When overwrite is False and the file exists already
        ValueError or TypeError
            When the file_type is not supported
        Exception
            When the extension save function raises an Error
        
        Parameters
        ----------
        file_path : str
            A valid path where the image to save including the file name and 
            the extension (if needed, the file_type paremeter is *never*
            appended to the file_path)
        overwrite : bool, optional
            Whether to overwrite the file_path if the file exists already, 
            default: True
        create_directories : bool, optional
            Whether to create the directories of the file_path if they do not 
            exist, default: False
        file_type : str or None
            None or 'auto' for automatic detection, the file_paths extension 
            will be used, this can be used to change the file type to something
            else that the extension if the file_path, this can be any key of 
            the `Image.export_extensions`, this is case-insensitive, 
            default: None
        
        Returns
        -------
        ExceptionThread
            The thread that is currently saving, the thread has started already
        """

        file_path = os.path.abspath(file_path)
        save_dir = os.path.dirname(file_path)

        if not os.path.isdir(save_dir) or not os.path.exists(save_dir):
            if create_directories:
                os.makedirs(save_dir, exist_ok=True)
            else:
                raise FileNotFoundError(
                    "The directory {} does not exist.".format(save_dir)
                )
        
        if (not overwrite and os.path.isfile(file_path) and 
            os.path.exists(file_path)):
            raise FileExistsError(
                "The file {} exists already and overwriting is not allowed.".format(
                    file_path
                )
            )
        
        if ((isinstance(file_type, str) and 
             file_type.lower() == "auto") or file_type == None):
            _, file_type = os.path.splitext(file_path)

        if isinstance(file_type, str):
            if file_type.startswith("."):
                file_type = file_type[1:]
            
            file_type = file_type.lower()

            thread = ExceptionThread(target=self._executeSave, 
                                     args=(file_type, file_path))
            thread.start()
            return thread
        else:
            raise TypeError(
                "The file extension {} is not supported.".format(file_type)
            )