

## setup the python env:

Navigate to Project Directory
```
cd RaspberryPiChessComputerSystem/
```
Create Virtual Environment
```
python -m venv venv
```
Activate Virtual Environment
```
source venv/bin/activate
```
Install Dependencies
```
pip install -r core/requirements.txt
```




## Configure drivers and libraries

Adjust `lv_conf.defaults` to select the drivers and libraries that will be compiled by
modifying the following definitions, setting them to `1` or `0`

You can also start with a default config based on the drivers you want to use,
you can find a default config for each graphic driver inside the configs folder.

You can either replace `lv_conf.defaults` manually or using CMake

```bash
cmake -B build -DCONFIG=<config_name> 
```
