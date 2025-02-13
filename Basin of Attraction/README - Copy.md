{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# <span style=\"color:red\"> Analytical Method</span>\n",
    "## *Estimating the Basin of Attraction*\n",
    "\n",
    "---\n",
    "---"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## **Overview**\n",
    "\n",
    "This code is to estimate the basin of attraction of any grid with any numbers of buses including meshed or radial."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### **Required libraries:**\n",
    "\n",
    "- NumPy: pip install numpy\n",
    "- Matplotlib: pip install matplotlib\n",
    "- Pandapower: pip install pandapower"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "#### ***Estimating_the_Basin_of_Attraction.ipynb***\n",
    "\n",
    "The provided code is written in Python and can be run for any grid. To change the grid, the *net* parameter need to be defined based on the desired network with the standard defined in pandapower library.\n",
    "\n",
    "The *v* parameter can be selected as slack bus voltage, the nominal voltages of the grid, or the voltages calculated in the privious run of power flow calculations.\n",
    "\n",
    "Other parameters can be easily extracted from the network."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "#### ***Results__Estimating_the_Basin_of_Attraction__7_Bus.png***\n",
    "\n",
    "One example of minimum and maximum radius of the basin of attraction for 7-bus system."
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
