import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PIL import Image as PILImage
import numpy as np
import time
import random
import pytest
import json
import pylo

image_counter = 0

class TestImage:
    def create_dummy_image(self, path):
        """Create a file that contains 128bytes of random data.

        Parameters
        ----------
        path : str
            The file path including the extension
        
        Returns
        -------
        str
            The path
        """
        f = open(path, "wb+")
        f.write(bytearray(random.getrandbits(8) for _ in range(128)))
        f.close()

        return path
    
    def get_random_image(self):
        """Create and return a random image.

        Returns
        -------
        Image
            The image object
        np.array_like
            A 128x128 array that contains the illumination data
        dict
            The tags
        """

        illumination_data = (np.random.rand(128, 128) * 255).astype(np.uint8)
        tags = {
            "first-test-value": 1,
            "second-test-value": "This is a string",
            "Third value contains": "Some spaces"
        }
        image = pylo.Image(illumination_data, tags)

        return image, illumination_data, tags
    
    def check_illumination_data(self, image, image_path):
        """Check whether the illumination data of the image and the image saved
        at the given path are the same.
        
        Parameters
        ----------
        image : Image
            The image object to check the illumination data of
        image_path : str
            A valid path of an existing image to check the data of
        
        Returns
        -------
        bool
            Whether the image illumination data is the same or not
        """
        
        load_img = np.array(PILImage.open(image_path))
        # print((load_img - image.image_data > 0).sum())
        return np.array_equal(image.image_data, load_img)
        # assert np.array_equiv(image.image_data, load_img)
        # assert np.allclose(image.image_data, load_img, rtol=2, atol=2)
    
    def check_tags(self, image, image_path):
        """Check whether the tags of the image and the image saved at the given 
        path are the same.
        
        Parameters
        ----------
        image : Image
            The image object to check the tags of
        image_path : str
            A valid path of an existing image to check the tags of
        
        Returns
        -------
        bool
            Whether the image tags are the same or not"""
        
        load_img = PILImage.open(image_path)
        tags = load_img.tag[pylo.config.TIFF_IMAGE_TAGS_INDEX]
        tags = tags[0]
        tags = json.loads(tags)
        return dict(image.tags) == dict(tags)
    
    def create_and_save_random_image(self, path, file_type):
        """Create a random Image object and save it.

        Parameters
        ----------
        path : str
            The file path where to save the image to including the file
            extension, if a {} is contained it will be replaces with the 
            current image counter
        file_type : str or None
            The file type, if None is give the save function will be called
            without the file_type (this means the default of the functino is 
            used and *not* None)

        Returns
        -------
        Image
            The created image object
        str
            The path where it is saved to
        """
        global image_counter

        image, data, tags = self.get_random_image()
        path = path.format(image_counter)

        image_counter += 1

        if file_type == None:
            thread = image.saveTo(path)
        else:
            thread = image.saveTo(path, file_type=file_type)
        
        # wait until the save is done, otherwise testing the result is not 
        # possible
        thread.join()
        
        return image, path

    @pytest.mark.parametrize("file_name,file_type", [
        ("test-image-{}.tif", None),
        ("test-image-{}.tiff", None),
        ("test-image-{}", "tif"),
        ("test-image-{}.jpg", "tif"),
        # do not test .jpg for equality, compression plus random data makes it
        # impossible to check whether the images are equal or not
        # ("test-image-{}.jpg", None),
        # ("test-image-{}.jpeg", None),
        # ("test-image-{}", "jpg"),
        # ("test-image-{}.tif", "jpg")
    ])
    def test_random_image_save_load_data(self, tmp_path, file_name, file_type):
        """Test if the saved illumination data is the same as the loaded one
        """
        
        image, path = self.create_and_save_random_image(
            os.path.join(tmp_path, file_name), file_type
        )
        assert self.check_illumination_data(image, path)

    @pytest.mark.parametrize("file_name,file_type", [
        ("test-image-{}.tif", None),
        ("test-image-{}.tiff", None),
        ("test-image-{}", "tif"),
        ("test-image-{}.jpg", "tif"),
    ])
    def test_random_image_save_load_tags(self, tmp_path, file_name, file_type):
        """Test if the saved tags is the same as the loaded one
        """

        image, path = self.create_and_save_random_image(
            os.path.join(tmp_path, file_name), file_type
        )
        assert self.check_tags(image, path)

    @pytest.mark.parametrize("file_name,overwrite", [
        # ("test-image-{}.jpg", True),
        ("test-image-{}.tif", True),
        # ("test-image-{}.jpg", None),
        ("test-image-{}.tif", None)
    ])
    def test_overwrite_image(self, tmp_path, file_name, overwrite):
        """Test if images are overwritten by default and if overwrite is True
        """
        global image_counter

        # create a random dummy image so the image exists already
        path = self.create_dummy_image(
            os.path.join(tmp_path, file_name.format(image_counter))
        )

        image, illumination_data, tags = self.get_random_image()

        if overwrite == None:
            thread = image.saveTo(path)
        else:
            thread = image.saveTo(path, overwrite=overwrite)
        
        # wait until the save is done, otherwise testing the result is not 
        # possible
        thread.join()
        
        assert self.check_illumination_data(image, path)

    @pytest.mark.parametrize("file_name,overwrite", [
        ("test-image-{}.jpg", True),
        ("test-image-{}.tif", True),
        ("test-image-{}.jpg", None),
        ("test-image-{}.tif", None)
    ])
    def test_by_file_time_overwrite_image(self, tmp_path, file_name, overwrite):
        """Test if images are overwritten by default and if overwrite is True
        """
        global image_counter

        # create a random dummy image so the image exists already
        path = self.create_dummy_image(
            os.path.join(tmp_path, file_name.format(image_counter))
        )
        creation_time = os.path.getmtime(path)

        image, illumination_data, tags = self.get_random_image()

        # make sure there is a difference in the times, otherwise sometimes 
        # this doesn't validate
        time.sleep(0.1)

        if overwrite == None:
            thread = image.saveTo(path)
        else:
            thread = image.saveTo(path, overwrite=overwrite)
        
        # wait until the save is done, otherwise testing the result is not 
        # possible
        thread.join()
        
        assert creation_time < os.path.getmtime(path)

    @pytest.mark.parametrize("file_name", [
        "test-image-{}.jpg",
        "test-image-{}.tif",
    ])
    def test_prevent_overwrite_image(self, tmp_path, file_name):
        """Test if images are overwritten by default and if overwrite is True
        """
        global image_counter

        # create a random dummy image so the image exists already
        path = self.create_dummy_image(
            os.path.join(tmp_path, file_name.format(image_counter))
        )

        image, illumination_data, tags = self.get_random_image()

        with pytest.raises(FileExistsError):
            thread = image.saveTo(path, overwrite=False)
        
            # wait until the save is done, otherwise testing the result is not 
            # possible
            thread.join()
    
    def test_create_directories(self, tmp_path):
        """Test if create_directories in saveTo creates the directories
        """
        global image_counter

        image, illumination_data, tags = self.get_random_image()
        
        dir_path = os.path.join(tmp_path, "auto-created-dir/")
        img_path = os.path.join(
            dir_path, "test-image-{}.tif".format(image_counter)
        )

        thread = image.saveTo(img_path, create_directories=True)
        
        # wait until the save is done, otherwise testing the result is not 
        # possible
        thread.join()

        assert os.path.exists(dir_path) and os.path.isdir(dir_path)
    
    def test_error_on_missing_parent_directory(self, tmp_path):
        """Test if saving raises an error if the parent directory does not 
        exist and the create_directories is False
        """
        global image_counter

        image, illumination_data, tags = self.get_random_image()
        dir_path = os.path.join(tmp_path, "non-existing-dir/")
        
        with pytest.raises(FileNotFoundError):
            thread = image.saveTo(
                os.path.join(dir_path, "test-image-{}.tif".format(image_counter)),
                create_directories=False
            )
        
            # wait until the save is done, otherwise testing the result is not 
            # possible
            thread.join()
    
    @pytest.mark.parametrize("file_name,file_type,PIL_expected_type", [
        ("test-image-{}.jpg", None, "JPEG"),
        ("test-image-{}.tif", None, "TIFF"),
        ("test-image-{}.jpeg", None, "JPEG"),
        ("test-image-{}.tiff", None, "TIFF"),
        ("test-image-{}", "jpg", "JPEG"),
        ("test-image-{}", "tif", "TIFF"),
        ("test-image-{}.tif", "jpg", "JPEG"),
        ("test-image-{}.jpg", "tif", "TIFF")
    ])
    def test_file_types(self, tmp_path, file_name, file_type, PIL_expected_type):
        """Test if the images are saved in the actual file types."""

        image, path = self.create_and_save_random_image(
            os.path.join(tmp_path, file_name), file_type
        )
        load_img = PILImage.open(path)

        assert load_img.format == PIL_expected_type
    
    @pytest.mark.parametrize("file_name,file_type", [
        ("test-image-{}.invalidtype1", None),
        ("test-image-{}", "invalidtype2"),
    ])
    def test_illegal_file_types(self, tmp_path, file_name, file_type):
        """Test if error is raised when the file extension is not known."""
        global image_counter

        image, illumination_data, tags = self.get_random_image()
        path = os.path.join(tmp_path, file_name.format(image_counter))

        image_counter += 1

        if file_type == None:
            with pytest.raises(ValueError):
                image.saveTo(path)
        else:
            with pytest.raises(ValueError):
                image.saveTo(path, file_type=file_type)
        
    
if __name__ == "__main__":
    t = TestImage()
    # t.setup_method()