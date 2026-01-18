# AOOSTAR GEM12 PRO MAX / GEM12+ PRO / WTR MAX Screen Control

### Main functionality : in progress

But you can use this code to turn your mini PC's screen on or off, and show some stuff on it. 
```
aoostar_screen.py [-h] [--on | --off] {image,i,text,t,panel,p} ...

Basic controls for Aoostar GEM12 PRO MAX or WTR MAX screens

positional arguments:
  {image,i,text,t,panel,p}
                        subcommands
    image (i)           Sends image to be displayed
    text (t)            Sends text to be displayed
    panel (p)           Sends Aoostar-X Panel to be displayed

options:
  -h, --help            show this help message and exit
  --on                  Powers screen on
  --off                 Powers screen off
```

You can show one frame of an Aoostar Style panel:
```
aoostar_screen.py panel [-h] [--hwinfo] panel_id [aoostar_internal_data_path]

positional arguments:
  panel_id              Id of the panel to be displayed
  aoostar_internal_data_path
                        Aoostar-X _internal path

options:
  --hwinfo              Get data from HWiNFO
```
Wth fictional data or real data on Windows if you have HWiNFO64 or HWiNFO32 running with the shared memory option enabled. 

Show some custom image with:
```
aoostar_screen.py image [-h] path

positional arguments:
  path        Image path

options:
  -h, --help  show this help message and exit
```

Or some simple text with:
```
aoostar_screen.py text [-h] content

positional arguments:
  content     Text to be displayed
```

The code provided is based on the reverse engineering published by [zehnm/aoostar-rs](https://github.com/zehnm/aoostar-rs).

My tests were made solely on a **GEM12 PRO MAX**.

Both **GEM12+ PRO** and the **GEM12 PRO MAX** use the same software variant with the same configs, so the **GEM12+ PRO** is expected to be compatible.

The **WTR MAX** is also selectable in the Aoostar-X software for the **GEM12+ PRO** and the **GEM12 PRO MAX**, with the only warning that TDPs are different; the reverse-engineered protocol in [zehnm/aoostar-rs](https://github.com/zehnm/aoostar-rs) was based on the **WTR MAX**, and so it is also expected to be compatible.

⚠ But, as a warning, independent of your mini PC model, there’s no guarantee that it’s going to function correctly or safely on your hardware. Be careful. ⚠

## Images

Panel images provided were reconstructed to look similar to Aoostar X's data, avoiding using ther artwork.
The Photoshop file with the reconstruction is available for possible further customization.

![default_1_hdd.jpeg](https://raw.githubusercontent.com/bro-santana/aoostar-screen-control/refs/heads/main/aoostar-x-compatible-data/sys_img/default_1_hdd.jpg)
![default_1_index.jpeg](https://raw.githubusercontent.com/bro-santana/aoostar-screen-control/refs/heads/main/aoostar-x-compatible-data/sys_img/default_1_index.jpg)

⚠ AI USE WARNING⚠ : There was no AI image generation used on default_1_hdd.jpg and default_1_index.jpg. There was AI image generation used to reconstruct the background from default_2_hdd.jpg,default_2_index.jpg,default_3_hdd.jpg,default_3_index.jpg,default_3_hdd.jpg and default_3_index.jpg to something similar to the original, I'm currently looking for alternative similar backgrounds.
