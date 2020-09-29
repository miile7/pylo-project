import os
import sys
import math
import typing
import pathlib

from .image import Image

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

try:
    import DigitalMicrograph as DM
except (ModuleNotFoundError, ImportError) as e:
    DM = None

if DM is not None:
    # for development only, execdmscript is another module that is developed
    # separately
    try:
        import dev_constants
        load_from_dev = True
    except (ModuleNotFoundError, ImportError) as e:
        load_from_dev = False

    if load_from_dev:
        if hasattr(dev_constants, "execdmscript_path"):
            if not dev_constants.execdmscript_path in sys.path:
                sys.path.insert(0, dev_constants.execdmscript_path)
            
    import execdmscript
else:
    raise ModuleNotFoundError("Could not load module execdmscript.")

class DMImage(Image):
    """An image that adds more export options and showing images.

    Attributes
    ----------
    show_image : bool
        Whether to display the image in a workspace or not
    workspace_id : int or None
        The workspace id to show the image in, if not an int the current 
        workspace will be used instead
    workspace_rect : tuple of int
        The workspace rect to place the images in with the order *top*, *left*,
        *bottom*, *right* containing the coordinate values
    shown_images_counter : int
        The number of images that are shown in the workspace
    """

    shown_images_counter = 0
    gatan_file_types = {
        "dm": "Gatan Format",
        "dm4": "Gatan Format",
        "gatan": "Gatan Format",
        "gatan format": "Gatan Format",
        "dm3": "Gatan 3 Format",
        "gatan 3 format": "Gatan 3 Format",
        "gif": "GIF Format",
        "bmp": "BMP Format",
        "jpg": "JPEG/JFIF Format",
        "jpeg": "JPEG/JFIF Format",
        "jfif": "JPEG/JFIF Format",
        "emf": "Enhanced Metafile Format",
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

        self.show_image = False
        self.workspace_id = None
        try:
            self.workspace_rect = self._getWorkspaceRect()
        except LookupError:
            self.workspace_rect = (0, 0, 512, 800)
        
        self._py_image = None

        super(DMImage, self).__init__(image_data, tags)
    
    def __del__(self):
        """Destruct the image object"""

        # delete the Py_Image reference, this should be automatically but just
        # to be sure
        del self._py_image
    
    def _getWorkspaceRect(self) -> typing.Tuple[int, int, int, int]:
        """Get the available workspace area in GMS.

        Raises
        ------
        LookupError
            When the workspace area could not be detected
        
        Returns
        -------
        tuple of int
            A tuple containing the *top*, *left*, *bottom* and *right* 
            coordinates of the available space for images in the stated order
        """

        readvars = {
            "top": int,
            "left": int,
            "bottom": int,
            "right": int
        }
        dmscript = "\n".join((
            "number top, left, bottom, right;",
            "GetMaximalDocumentWindowRect(1+2+240, top, left, bottom, right);"
        ))

        workspace_rect = None
        with execdmscript.exec_dmscript(dmscript, readvars=readvars) as script:
            workspace_rect = (script["top"], script["left"], script["bottom"], 
                              script["right"])
        
        if not isinstance(workspace_rect, tuple):
            raise LookupError("Could not detect the workspace area in GMS.")
            
        return workspace_rect
    
    @classmethod
    def fromDMPyImageObject(cls: typing.Any, image: DM.Py_Image, 
                          additional_tags: typing.Optional[dict]={}) -> "DMImage":
        """Create the `DMImage` from the given DigitalMicrograph image object.

        Parameters
        ----------
        image : DigitalMicrograph.Py_Image
            The DM image object
        additional_tags : dict, optional
            Additional tags to add to the image tags
        
        Returns
        -------
        DMImage
            The DMImage object
        """

        additional_tags = {}
        img = DMImage(image.GetNumArray(), additional_tags)
        img._py_image = image
        
        return img
    
    def _executeSave(self, file_type: str, file_path: str) -> None:
        """Execute the save.

        This adds 

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

        if file_type in DMImage.gatan_file_types:
            name, _ = os.path.splitext(os.path.basename(file_path))
            image_doc = self._getImageDocument(name)
            
            # mentioned formats are 'Gatan Format', 'Gatan 3 Format, 
            # 'GIF Format', 'BMP Format', 'JPEG/JFIF Format', 
            # 'Enhanced Metafile Format'
            image_doc.SaveToFile(DMImage.gatan_file_types[file_type], file_path)

            if self.show_image:
                self._show(image_doc, self.workspace_id, file_path)
            elif isinstance(self._py_image, DM.Py_Image):
                # image is saved, drop the Py_Image reference for memory leaks,
                # this is recommended in the docs
                del self._py_image
        else:
            super(DMImage, self)._executeSave(file_type, file_path)
    
    def getDMPyImageObject(self, name: typing.Optional[str]=None) -> DM.Py_Image:
        """Get the DigitalMicrograph.Py_Image for the current image.

        Note that the dm image is not linked to the file, even if the image 
        has been saved already. This is because there is no python function to
        linking the image to the file at the moment.

        Parameters
        ----------
        name : str, optional
            The name of the image, if not a string the image will have the name 
            generated by GMS, default: None

        Returns
        -------
        DigitalMicrograph.Py_Image
            The DM image object
        """

        if not isinstance(self._py_image, DM.Py_Image):
            img = DM.CreateImage(self.image_data)
        else:
            img = self._py_image
        
        # save the tags
        if isinstance(self.tags, dict) and self.tags != {}:
            tag_group = execdmscript.convert_to_taggroup(self.tags)
            img.GetTagGroup().CopyTagsFrom(tag_group)
        
        # set the name
        if isinstance(name, str):
            img.SetName(name)
        
        return img

    def _getImageDocument(self, name: typing.Optional[str]=None) -> DM.Py_ImageDocument:
        """Get the image document.

        Note that the document is not linked to the file, even if the image 
        has been saved already. This is because there is no python function to
        linking the image to the file at the moment.

        Parameters
        ----------
        name : str, optional
            The name of the image document and the image itself, if not a 
            string the image will have the name generated by GMS, default: None

        Returns
        -------
        DigitalMicrograph.Py_ImageDocument
            The DM image document object
        """

        img = self.getDMPyImageObject(name)
        
        # create an image document that contains the image
        # image_doc = DM.NewImageDocument(name)
        # image_doc.AddImageDisplay(img, -2)
        image_doc = img.GetOrCreateImageDocument()

        if isinstance(name, str):
            image_doc.SetName(name)
        
        return image_doc
    
    def show(self, name: typing.Optional[str]=None, 
             workspace_id: typing.Optional[int]=None,
             file_path: typing.Optional[typing.Union[pathlib.PurePath, str]]=None) -> DM.Py_ImageDocument:
        """Show the image.

        If the `workspace_id` is given, the image will be shown in this 
        workspace.

        Parameters
        ----------
        name : str, optional
            The name of the image document and the image itself, if not a 
            string the image will have the name generated by GMS, default: None
        workspace_id: int, optional
            The workspace id to show in, if not an int the image will be shown 
            in the current workspace, default: None
        file_path : str or pathlib.PurePath, optional
            The path where the image is
        
        Returns
        -------
        DigitalMicrograph.Py_ImageDocument
            The image document that shows the image
        """

        image_doc = self._getImageDocument(name)
        return self._show(image_doc, workspace_id, file_path)
    
    def _show(self, image_doc: DM.Py_ImageDocument, 
              workspace_id: typing.Optional[int]=None,
              file_path: typing.Optional[typing.Union[pathlib.PurePath, str]]=None) -> DM.Py_ImageDocument:
        """Show the given image document.

        If the `workspace_id` is given, the image will be shown in this 
        workspace.

        Parameters
        ----------
        image_doc : DigitalMicrograph.Py_ImageDocument
            The image document to show
        workspace_id: int, optional
            The workspace id to show in, if not an int the image will be shown 
            in the current workspace, default: None
        file_path : str or pathlib.PurePath, optional
            The path where the image is
        
        Returns
        -------
        DigitalMicrograph.Py_ImageDocument
            The image document that shows the image
        """
        if isinstance(workspace_id, int):
            image_doc.MoveToWorkspace(workspace_id)
        
        # calculate position depending on the available size and the 
        # number of columns
        from .config import DEFAULT_DM_SHOW_IMAGES_ROW_COUNT
        rows = DEFAULT_DM_SHOW_IMAGES_ROW_COUNT

        length = round(
            (self.workspace_rect[2] - self.workspace_rect[0]) / rows
        )
        cols = math.floor(
            (self.workspace_rect[3] - self.workspace_rect[1]) / length
        )
        row_index = (DMImage.shown_images_counter // cols) % rows
        col_index = (DMImage.shown_images_counter % cols)
        pos = (
            self.workspace_rect[0] + row_index * length, 
            self.workspace_rect[1] + col_index * length, 
            self.workspace_rect[0] + (row_index + 1) * length, 
            self.workspace_rect[1] + (col_index + 1) * length
        )

        # show in the workspace
        image_doc.ShowAtRect(*pos)

        # link to file
        if isinstance(file_path, str) or isinstance(file_path, pathlib.PurePath):
            if isinstance(workspace_id, int):
                wsid = workspace_id
            else:
                wsid = ""
            
            dmscript = "\n".join((
                "for(number i = CountImageDocuments({}) - 1; i >= 0; i--){{".format(wsid),
                    "ImageDocument img_doc = GetImageDocument(i, {});".format(wsid),
                    "if(img_doc.ImageDocumentGetName() == name){",
                        "img_doc.ImageDocumentSetCurrentFile(path);",
                        "if(format != \"\"){",
                            "img_doc.ImageDocumentSetCurrentFileSaveFormat(format);",
                        "}",
                        "break;",
                    "}",
                "}"
            ))

            _, extension = os.path.splitext(file_path)

            if extension in DMImage.gatan_file_types:
                file_format = DMImage.gatan_file_types[extension]
            else:
                file_format = ""
            
            svars = {
                "name": image_doc.GetName(),
                "path": file_path,
                "format": file_format
            }

            with execdmscript.exec_dmscript(dmscript, setvars=svars):
                pass

        DMImage.shown_images_counter += 1

        return image_doc