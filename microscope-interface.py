class MicroscopeInterface:
    """
    An interface class to communicate with the microscope.
    """

    async def setInLorenzMode(self, lorenz_mode):
        """
        Set whether the microscope should now be in lorenz mode or not.

        Parameters
        ----------
        lorenz_mode : boolean
            Whether to put the microscope in lorenz mode or not
        """
        raise NotImplementedError()

    async def getInLorenzMode(self):
        """
        Get whether the microscope is currently in lorenz mode or not.

        Returns
        -------
        boolean
            Whether the microscope is in lorenz mode or not
        """
        raise NotImplementedError()

    async def setFocus(self, focus):
        """
        Set the focus current in the microscope specific units.

        Parameters
        ----------
        focus : int or float
            The focus current
        """
        raise NotImplementedError()

    async def getFocus(self):
        """
        Get the focus current in the microscope specific units.

        Returns
        -------
        int or float
            The focus current
        """
        raise NotImplementedError()

    async def setMagneticField(self, focus):
        """
        Set the magnetic field in the microscope specific units.

        Parameters
        ----------
        focus : int or float
            The magnetic field
        """
        raise NotImplementedError()

    async def getMagneticField(self):
        """
        Get the magnetic field in the microscope specific units.

        Returns
        -------
        int or float
            The magnetic field
        """
        raise NotImplementedError()

    async def getIsTiltDirectionSupported(self, x_or_y):
        """
        Get Whether the microscope (holder) supports tilting in x or y 
        direction.

        Parameters
        ----------
        x_or_y : str
            The tilt direction to check, "x" for checking the x direction and 
            "y" for checking the y direction

        Returns
        -------
        boolean
            Whether the microscope supports the tilting direction or not
        """
        raise NotImplementedError()

    async def setTilt(self, x_tilt, y_tilt):
        """
        Set the tilt in x and/or y direction in the microscope specific units.

        Parameters
        ----------
        x_tilt : int or float
            The tilt in x direction
        y_tilt : int or float
            The tilt in y direction
        """
        raise NotImplementedError()

    async def getTilt(self):
        """
        Get the tilt in x and/or y direction in the microscope specific units.

        Returns
        ----------
        tuple of int or tuple of float
            The tilt in x direction at index 0, the tilt in y direction at 
            index 1
        """
        raise NotImplementedError()