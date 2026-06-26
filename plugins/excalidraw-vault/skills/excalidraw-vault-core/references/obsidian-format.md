# Obsidian Excalidraw file template

Copy-pasteable template for a vault-native Excalidraw diagram. Replace the `elements` array with your generated content.

````
---
excalidraw-plugin: parsed
tags: [excalidraw]
---

==⚠ Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'

# Excalidraw Data

## Text Elements

%%
## Drawing
```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
  "elements": [
    {
      "id": "node-1",
      "type": "rectangle",
      "x": 100, "y": 100,
      "width": 200, "height": 80,
      "angle": 0,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#a5d8ff",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "roundness": { "type": 3 },
      "seed": 123456789,
      "version": 1,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1,
      "link": null,
      "locked": false
    },
    {
      "id": "label-1",
      "type": "text",
      "x": 130, "y": 130,
      "width": 140, "height": 24,
      "angle": 0,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "roundness": null,
      "seed": 987654321,
      "version": 1,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1,
      "link": null,
      "locked": false,
      "text": "Vault",
      "fontSize": 20,
      "fontFamily": 5,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18
    }
  ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```
%%
````

## Critical bits

- Two outer `---` lines for frontmatter — nothing between them except the two keys.
- The warning banner line stays exactly as shown (it's what the plugin checks for to recognize the file).
- `## Text Elements` is followed by an empty line then `%%`. The plugin auto-fills text references.
- JSON fence opens with ```json (3 backticks + json).
- File ends with `%%` after the JSON fence closes.
