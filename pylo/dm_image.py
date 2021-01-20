import os
import sys
import math
import typing
import logging
import pathlib

from .errors import ExecutionOutsideEnvironmentError
# python <3.6 does not define a ModuleNotFoundError, use this fallback
from .errors import FallbackModuleNotFoundError

try:
    import DigitalMicrograph as DM
except (FallbackModuleNotFoundError, ImportError) as e:
    DM = None

if DM is not None:
    # for development only, execdmscript is another module that is developed
    # separately
    try:
        import dev_constants
        load_from_dev = True
    except (FallbackModuleNotFoundError, ImportError) as e:
        load_from_dev = False

    if load_from_dev:
        if hasattr(dev_constants, "execdmscript_path"):
            if not dev_constants.execdmscript_path in sys.path:
                sys.path.insert(0, dev_constants.execdmscript_path)
            
    import execdmscript
else:
    raise ExecutionOutsideEnvironmentError("Could not load module execdmscript.")

from .image import Image
from .logginglib import log_debug
from .logginglib import log_error
from .logginglib import get_logger
from .logginglib import do_log

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
    annotations : list of str
        A list of annotations, if 'scalebar' is used, a scalebar is added, 
        everything else will be added as text
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

        super(DMImage, self).__init__(image_data, tags)

        self._logger = get_logger(self)

        self.show_image = False
        self.annotations = []
        self.workspace_id = None
        try:
            self.workspace_rect = self._getWorkspaceRect()
        except LookupError:
            self.workspace_rect = (0, 0, 512, 800)
        
        self._py_image = None
    
    def __del__(self):
        """Destruct the image object"""

        # delete the Py_Image reference, this should be automatically but just
        # to be sure
        if hasattr(self, "_py_image"):
            log_debug(self._logger, ("Deleting this instance but deleting " + 
                                    "the _py_image attribute before"))
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

        log_debug(self._logger, "Trying to get the workspace rect")

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

        log_debug(self._logger, "Executing dm-script '{}' with readvars '{}'".format(
                            dmscript, readvars))
        workspace_rect = None
        with execdmscript.exec_dmscript(dmscript, readvars=readvars) as script:
            workspace_rect = (script["top"], script["left"], script["bottom"], 
                              script["right"])
        
        log_debug(self._logger, ("Found workspace rect to be " + 
                                 "'{}'").format(workspace_rect))
        
        if not isinstance(workspace_rect, tuple):
            err = LookupError("Could not detect the workspace area in GMS.")
            log_error(self._logger, err)
            raise err
            
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

        # additional_tags = {}
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

            from .config import DM_IMAGE_DISABLE_PYTHON_ANNOTATIONS
            if not DM_IMAGE_DISABLE_PYTHON_ANNOTATIONS:
                # annotations do not work yet, check out DMImage._addAnnotations()
                # for details
                image_doc = self._addAnnotations(image_doc)

            log_debug(self._logger, ("Saving image by dm image document " + 
                                     "'{}' with the file type '{}' to the " + 
                                     "path '{}'").format(image_doc, file_type, 
                                        file_path))
            
            # mentioned formats are 'Gatan Format', 'Gatan 3 Format, 
            # 'GIF Format', 'BMP Format', 'JPEG/JFIF Format', 
            # 'Enhanced Metafile Format'
            image_doc.SaveToFile(DMImage.gatan_file_types[file_type], file_path)

            if self.show_image:
                self._show(image_doc, self.workspace_id, file_path)
            elif isinstance(self._py_image, DM.Py_Image):
                # image is saved, drop the Py_Image reference for memory leaks,
                # this is recommended in the docs
                log_debug(self._logger, "Deleting _py_image reference")
                del self._py_image
        else:
            log_debug(self._logger, ("Saving image by parent class Image with " + 
                                    "the file type '{}' to the path '{}'").format(
                                    file_type, file_path))
            super(DMImage, self)._executeSave(file_type, file_path)
    
    def _addAnnotations(self, image_doc: DM.Py_ImageDocument) -> DM.Py_ImageDocument:
        """Add the annotations defined by `DMImage.annotations` to the image.

        The annotations will be added to the first `ImageDisplay` of the image
        document. If there is no image in the image document, nothing will 
        happen. If there is no display, the display will be created 
        automatically.

        The `DMImage.annotations` can be a list of annotations. All annotations
        will be added to the bottom from left to right. The color and the
        dimensions can be set by the corresponding constants in the `config.py`

        Note that if too many annotations are given, they will simply overflow 
        and run out of the image. Also the alignment and the spacing is not 
        done perfectly.

        See also
        --------
        config.DM_IMAGE_ANNOTATION_COLOR
        config.DM_IMAGE_ANNOTATION_PADDING_FRACTION
        config.DM_IMAGE_ANNOTATION_SCALEBAR_LENGTH_FRACTION
        config.DM_IMAGE_ANNOTATION_HEIGHT_FRACTION

        Raises
        ------
        NotImplementedError
            Annotations do not work yet at all. There is an internal problem 
            with loosing references to the image display of the image document.
            Every time modifying the display, a copy of this display object is 
            created so the image documents display does remain untouched. This 
            way it is not possible to add annotations.
            Check out the comments of 
            https://stackoverflow.com/a/65790891/5934316 where this is stated.
            Additionally some email contact with GMS (=DigitalMicrograph module)
            developers confirmed that this does not work at all

        Parameters
        ----------
        image_doc : DM.Py_ImageDocument
            The image document

        Returns
        -------
        DM.Py_ImageDocument
            The image document with the first display containing the 
            annotations
        """
        raise NotImplementedError(
            "Adding annotations is implemented but does currently not work " + 
            "due to reference problems inside the DigitalMicrograph module. " + 
            "Check out the function comments for more details. \n\n" + 
            "If you are not a developer and you see this error just ignore it. " + 
            "The requested feature does not work and there is nothing you " + 
            "can do to make it work."
        )

        if not isinstance(self.annotations, list) or len(self.annotations) == 0:
            log_debug(self._logger, ("Skipping adding annotations '{}', " + 
                                     "annotations are not a list or empty").format(
                                         self.annotations))
        else:
            log_debug(self._logger, ("Adding annotations to '{}' images " + 
                                     "in document").format(image_doc.CountImages()))
            
            from .config import DM_IMAGE_ANNOTATION_COLOR
            from .config import DM_IMAGE_ANNOTATION_PADDING_FRACTION
            from .config import DM_IMAGE_ANNOTATION_SCALEBAR_LENGTH_FRACTION
            from .config import DM_IMAGE_ANNOTATION_HEIGHT_FRACTION

            display_type = 20

            if not isinstance(image_doc.GetRootComponent(), DM.Py_Component):
                log_debug(self._logger, ("Cannot add annotations, the root " + 
                                         "component '{}' of the image display " + 
                                         "is not a Py_Component but a " + 
                                         "component of type '{}'").format(
                                             image_doc.GetRootComponent(),
                                             image_doc.GetRootComponent().GetType()))
            elif image_doc.GetRootComponent().CountChildrenOfType(display_type) == 0:
                log_debug(self._logger, ("Cannot add annotations, the root " + 
                                         "component of the image display " + 
                                         "does not contain a child of type " + 
                                         "'{}' (= image display)").format(
                                             display_type))
            elif image_doc.CountImages() == 0:
                log_debug(self._logger, ("Cannot add annotations, the image " + 
                                         "document does not contain any " + 
                                         "images"))
            else:
                # dm-script does not return the original image here but a 
                # copy so any modifications applied to the `img` are ignored
                img_clone = image_doc.GetImage(0)
                log_debug(self._logger, ("Adding annotations to image ('{}') " + 
                                         "to display '{}'").format(
                                             img_clone.GetName(), 
                                             image_doc.GetRootComponent().GetNthChildOfType(display_type, 0)))

                image_width = img_clone.GetDimensionSize(0)
                image_height = img_clone.GetDimensionSize(1)

                t = (1 - DM_IMAGE_ANNOTATION_HEIGHT_FRACTION - 
                        DM_IMAGE_ANNOTATION_PADDING_FRACTION) * image_height
                l = DM_IMAGE_ANNOTATION_PADDING_FRACTION * image_width

                for annotation in self.annotations:
                    log_debug(self._logger, ("Trying to add annotation " + 
                                             "'{}'").format(annotation))
                    if annotation == "scalebar":
                        b = ((1 - DM_IMAGE_ANNOTATION_PADDING_FRACTION) * 
                                image_height)
                        r = (l + DM_IMAGE_ANNOTATION_SCALEBAR_LENGTH_FRACTION * 
                                image_width)
                        # do not save the root component, otherwise a copy is 
                        # created
                        annotation = image_doc.GetRootComponent().GetNthChildOfType(display_type, 0).AddNewComponent(31, t, l, b, r)
                    else:
                        continue
                        # annotation = DM.NewTextAnnotation(l, t, annotation,
                        #     DM_IMAGE_ANNOTATION_PADDING_FRACTION * image_height)
                        # do not save the root component, otherwise a copy is 
                        # created
                        # image_doc.GetRootComponent().GetNthChildOfType(display_type, 0).?
                        # annotation = DM.NewTextAnnotation(13, l, t, 
                        #     annotation, 
                        #     DM_IMAGE_ANNOTATION_HEIGHT_FRACTION * image_height)
                    
                    annotation.SetForegroundColor(
                        DM_IMAGE_ANNOTATION_COLOR[0],
                        DM_IMAGE_ANNOTATION_COLOR[1],
                        DM_IMAGE_ANNOTATION_COLOR[2])
                    
                    bounding_rect = annotation.GetBoundingRect()
                    # get right value of bounding rect
                    l = (bounding_rect[3] + 
                            DM_IMAGE_ANNOTATION_PADDING_FRACTION * image_width)
                    
                    log_debug(self._logger, ("Added annotation '{}' of " + 
                                             "type '{}' with bounding rect " + 
                                             "'{}' and color '{}'").format(
                                                 annotation, 
                                                 annotation.GetType(),
                                                 bounding_rect, 
                                                 annotation.GetForegroundColor()))
                    
                if do_log(self._logger, logging.DEBUG):
                    n = image_doc.GetRootComponent().GetNthChildOfType(display_type, 0).CountChildren()
                    added_annotations = "{} annotations: [".format(n)
                    for i in range(n):
                        added_annotations += "{}: type={}, ".format(i, 
                            image_doc.GetRootComponent().GetNthChildOfType(display_type, 0).GetChild(i).GetType())
                    added_annotations += "]"

                    log_debug(self._logger, ("Image document '{}' display " + 
                                             "contains the following " + 
                                             "annotations: {}").format(
                                                 image_doc, added_annotations))
                                                
        return image_doc
        
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

        log_debug(self._logger, "Creating DigitalMicrograph.Py_Image object from " + 
                            "current image")

        if not isinstance(self._py_image, DM.Py_Image):
            img = DM.CreateImage(self.image_data)
        else:
            img = self._py_image
        
        log_debug(self._logger, ("Created DigitalMicrograph.Py_Image object " + 
                                 "'{}'").format(img))
        
        # save the tags
        if isinstance(self.tags, dict) and self.tags != {}:
            log_debug(self._logger, ("Converting dict tags '{}' to " + 
                                    "DigitalMicrograph.Py_TagGroup").format(self.tags))
            tag_group = execdmscript.convert_to_taggroup(
                self.tags, replace_invalid_chars=True)
            log_debug(self._logger, ("Copying DigitalMicrograph.Py_TagGroup tags " + 
                                    "'{}' to image").format(tag_group))
            img.GetTagGroup().CopyTagsFrom(tag_group)
        
        # set the name
        if isinstance(name, str):
            img.SetName(name)
        
        log_debug(self._logger, "Returning DigitalMicrograph.Py_Image object")
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
        
        log_debug(self._logger, "Trying to get image document of " + 
                            "DigitalMicrograph.Py_Image object '{}'".format(img))
        # create an image document that contains the image
        # image_doc = DM.NewImageDocument(name)
        # image_doc.AddImageDisplay(img, -2)
        image_doc = img.GetOrCreateImageDocument()

        log_debug(self._logger, ("Got DigitalMicrograph.Py_ImageDocument object " + 
                                "'{}'").format(image_doc))

        if isinstance(name, str):
            image_doc.SetName(name)
        
        log_debug(self._logger, "Returning image object")
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

        log_debug(self._logger, "Showing image '{}'".format(name))
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
        log_debug(self._logger, ("Showing image with " + 
                                 "DigitalMicrograph.Py_ImageDocument '{}'").format(
                                image_doc))
        if (isinstance(workspace_id, int) and 
            DM.WorkspaceCountWindows(workspace_id) > 0):
            log_debug(self._logger, "Moving image document '{}' to workspace '{}'".format(
                                    image_doc, workspace_id))
            # check if the workspace exists (if not it does not have windows),
            # if the workspace does not exist and ImageDocument.MoveToWorkspace()
            # is called, a RuntimeError is raised
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

        log_debug(self._logger, "Setting image document to position '{}'".format(pos))
        # show in the workspace
        image_doc.ShowAtRect(*pos)

        from .config import DM_IMAGE_DISABLE_PYTHON_ANNOTATIONS

        # link to file and/or add annotations
        if (isinstance(file_path, str) or 
            isinstance(file_path, pathlib.PurePath) or 
            (DM_IMAGE_DISABLE_PYTHON_ANNOTATIONS and 
             isinstance(self.annotations, (list, tuple)))):
            if isinstance(workspace_id, int):
                wsid = workspace_id
            else:
                wsid = ""
            
            dmscript = []
            if (DM_IMAGE_DISABLE_PYTHON_ANNOTATIONS and 
                isinstance(self.annotations, (list, tuple))):
                # do not link to file because annotations are missing in the
                # file, force user to save the workspace

                log_debug(self._logger, ("Adding annotations in dm-script " + 
                                         "after showing the file, not " + 
                                         "linking to file because in file " + 
                                         "the annotations are missing."))
            
                from .config import DM_IMAGE_ANNOTATION_COLOR
                from .config import DM_IMAGE_ANNOTATION_PADDING_FRACTION
                from .config import DM_IMAGE_ANNOTATION_SCALEBAR_LENGTH_FRACTION
                from .config import DM_IMAGE_ANNOTATION_HEIGHT_FRACTION

                dmscript += [
                    "if(img_doc.ImageDocumentCountImages() > 0){",
                        "Image img := img_doc.ImageDocumentGetImage(0);",
                        "ImageDisplay display;",
                        "if(img.ImageCountImageDisplays() == 0){",
                            "display = img_doc.ImageDocumentAddImageDisplay(img, -2);",
                        "}",
                        "else{",
                            "display = img.ImageGetImageDisplay(0);",
                        "}",
                        "Component annotation;",
                        "number image_width = img.ImageGetDimensionSize(0);",
                        "number image_height = img.ImageGetDimensionSize(1);",
                        "number top, left, bottom, right, font_size, t, l, b, r;",
                        "top = (1 - {ah} - {ap}) * image_height".format(
                            ah=DM_IMAGE_ANNOTATION_HEIGHT_FRACTION,
                            ap=DM_IMAGE_ANNOTATION_PADDING_FRACTION),
                        "left = {ap} * image_width".format(
                            ap=DM_IMAGE_ANNOTATION_PADDING_FRACTION),
                        "font_size = {ah} * image_height".format(
                            ah=DM_IMAGE_ANNOTATION_HEIGHT_FRACTION)
                ]

                for annotation in self.annotations:
                    log_debug(self._logger, ("Trying to add annotation " + 
                                             "'{}'").format(annotation))
                                             
                    if annotation == "scalebar":
                        dmscript += [
                            "bottom = (1 - {ap}) * image_height".format(
                                ap=DM_IMAGE_ANNOTATION_PADDING_FRACTION),
                            "right = left + {sl} * image_width".format(
                                sl=DM_IMAGE_ANNOTATION_SCALEBAR_LENGTH_FRACTION),
                            "annotation = NewComponent(31, top, left, bottom, right);"
                        ]
                    else:
                        dmscript += [
                            "annotation = NewTextAnnotation(left, top, \"{}\", font_size);".format(
                                execdmscript.escape_dm_string(annotation))
                        ]
                    
                    dmscript += [
                        "annotation.ComponentSetForegroundColor({r}, {g}, {b})".format(
                            r=DM_IMAGE_ANNOTATION_COLOR[0], 
                            g=DM_IMAGE_ANNOTATION_COLOR[1],
                            b=DM_IMAGE_ANNOTATION_COLOR[2]),
                        "display.ComponentAddChildAtEnd(annotation);",
                        "annotation.ComponentGetBoundingRect(t, l, b, r);",
                        "left = r + {ap} * image_width;".format(
                            ap=DM_IMAGE_ANNOTATION_PADDING_FRACTION)
                    ]
                    
                dmscript += [
                    "}"
                ]
            else:
                log_debug(self._logger, "Trying to link image document to the file")
                dmscript = [
                    "if(path != \"\"){",
                        "img_doc.ImageDocumentSetCurrentFile(path);",
                        "if(format != \"\"){",
                            "img_doc.ImageDocumentSetCurrentFileSaveFormat(format);",
                        "}",
                        "img_doc.ImageDocumentClean();",
                    "}"
                ]
            
            dmscript = "\n".join([
                "number wsid = {}".format("WorkspaceGetActive();" if wsid == "" 
                                          else wsid),
                "if(WorkspaceGetIndex(wsid) >= 0){",
                    "for(number i = CountImageDocuments(wsid) - 1; i >= 0; i--){",
                        "ImageDocument img_doc = GetImageDocument(i, wsid);",
                        "if(img_doc.ImageDocumentGetName() == name){"
                            ] + 
                                dmscript + 
                            [
                            "break;",
                        "}",
                    "}",
                "}"
            ])
            
            if (isinstance(file_path, str) or 
                isinstance(file_path, pathlib.PurePath)):
                _, extension = os.path.splitext(file_path)

                if extension in DMImage.gatan_file_types:
                    file_format = DMImage.gatan_file_types[extension]
                else:
                    file_format = ""
            else:
                file_path = ""
                file_format = ""
            
            svars = {
                "name": image_doc.GetName(),
                "path": file_path,
                "format": file_format
            }

            log_debug(self._logger, "Executing dmscript '{}' with setvars '{}'".format(
                                dmscript, svars))
            with execdmscript.exec_dmscript(dmscript, setvars=svars):
                pass
        
        DMImage.shown_images_counter += 1

        return image_doc