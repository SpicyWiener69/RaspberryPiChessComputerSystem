# Chess UI on top of LVGL
LVGL provides drivers for many graphics backends.
Legacy framebuffer (fbdev), modern DRM/KMS, Wayland, X11, GLFW3 and SDL2.

Check out this blog post for a step by step tutorial for fbdev
https://blog.lvgl.io/2018-01-03/linux_fb

## Configure drivers and libraries

Adjust `lv_conf.defaults` to select the drivers and libraries that will be compiled by
modifying the following definitions, setting them to `1` or `0`

You can also start with a default config based on the drivers you want to use,
you can find a default config for each graphic driver inside the configs folder.

You can either replace `lv_conf.defaults` manually or using CMake

```bash
cmake -B build -DCONFIG=<config_name> 
```

With `<config_name>` the name of the config without the `.defaults` extension, eg: `configs/wayland.defaults` becomes `wayland`.

## Install dependencies

Be sure to install the required dependencies for the selected drivers by checking
the documentation for each driver here:
https://docs.lvgl.io/master/details/integration/driver/

You can also check the [Dockerfiles](docker/) to get the names
of the packages for various distributions

## Build instructions

### CMake

```
cmake -B build
cmake --build build -j$(nproc)
```

## Run the chess UI application

```
./build/bin/lvglsim
```

## Environment variables

Environment variables can be set to modify the behavior of the driver(s)
Check the documentation of the drivers for more details


### Legacy framebuffer (fbdev)

- `LV_LINUX_FBDEV_DEVICE` - override default (`/dev/fb0`) framebuffer device node.


### EVDEV touchscreen/mouse pointer device

- `LV_LINUX_EVDEV_POINTER_DEVICE` - the path of the input device, i.e.
  `/dev/input/by-id/my-mouse-or-touchscreen`. If not set, devices will
  be discovered and added automatically.

### DRM/KMS

- `LV_LINUX_DRM_CARD` - override default (`/dev/dri/card0`) card.

### Simulator

- `LV_SIM_WINDOW_WIDTH` - width of the window (default `800`).
- `LV_SIM_WINDOW_HEIGHT` - height of the window (default `480`).


## Permissions

By default, unpriviledged users don't have access to the framebuffer device `/dev/fb0`. In such cases, you can either run the application
with `sudo` privileges or you can grant access to the `video` group.
