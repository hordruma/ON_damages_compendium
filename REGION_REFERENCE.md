# Anatomical Region Reference Guide

## Complete List of Region IDs

This document lists all clickable regions in the body diagrams and their corresponding clinical labels and compendium terms.

## Region IDs for SVG Files

When creating or modifying SVG body diagrams, use these exact `id=""` values:

### Head & Spine (5 regions)

| Region ID | Clinical Label | Common Terms |
|-----------|----------------|--------------|
| `head` | Cranial / Facial Structures | head, skull, brain, facial, cranial, concussion, TBI, facial fracture |
| `cervical_spine` | Cervical Spine (C1-C7) | neck, cervical, whiplash, C1-C7, facet joint, radiculopathy |
| `thoracic_spine` | Thoracic Spine (T1-T12) | thoracic, upper back, mid back, T1-T12 |
| `lumbar_spine` | Lumbar Spine (L1-S1) | lumbar, lower back, low back, L1-L5, disc herniation, sciatica |
| `sacroiliac` | Sacroiliac Joint | sacroiliac, SI joint, sacrum, coccyx, tailbone |

### Torso (3 regions)

| Region ID | Clinical Label | Common Terms |
|-----------|----------------|--------------|
| `chest` | Thoracic Cage / Ribs | chest, ribs, rib fracture, sternum, costal |
| `abdomen` | Abdominal Region | abdomen, abdominal, stomach, internal organs, spleen, liver |
| `pelvis` | Pelvic Ring | pelvis, pelvic, pelvic fracture, pubic symphysis |

### Left Upper Limb (6 regions)

| Region ID | Clinical Label | Common Terms |
|-----------|----------------|--------------|
| `shoulder_left` | Left Glenohumeral / AC Complex | left shoulder, glenohumeral, rotator cuff, AC joint, clavicle |
| `arm_left` | Left Humerus / Brachial Region | left arm, left upper arm, humerus, brachial, bicep, tricep |
| `elbow_left` | Left Elbow (Olecranon / Radiocapitellar) | left elbow, olecranon, radiocapitellar, tennis elbow |
| `forearm_left` | Left Forearm (Ulna / Radius) | left forearm, ulna, radius, forearm fracture |
| `wrist_left` | Left Wrist (Radiocarpal Joint) | left wrist, radiocarpal, carpal, scaphoid, TFCC |
| `hand_left` | Left Hand (Metacarpals / Digits) | left hand, metacarpal, finger, thumb, digit, grip loss |

### Right Upper Limb (6 regions)

| Region ID | Clinical Label | Common Terms |
|-----------|----------------|--------------|
| `shoulder_right` | Right Glenohumeral / AC Complex | right shoulder, glenohumeral, rotator cuff, AC joint, clavicle |
| `arm_right` | Right Humerus / Brachial Region | right arm, right upper arm, humerus, brachial, bicep, tricep |
| `elbow_right` | Right Elbow (Olecranon / Radiocapitellar) | right elbow, olecranon, radiocapitellar, tennis elbow |
| `forearm_right` | Right Forearm (Ulna / Radius) | right forearm, ulna, radius, forearm fracture |
| `wrist_right` | Right Wrist (Radiocarpal Joint) | right wrist, radiocarpal, carpal, scaphoid, TFCC |
| `hand_right` | Right Hand (Metacarpals / Digits) | right hand, metacarpal, finger, thumb, digit, grip loss |

### Left Lower Limb (6 regions)

| Region ID | Clinical Label | Common Terms |
|-----------|----------------|--------------|
| `hip_left` | Left Acetabulofemoral Joint | left hip, acetabulum, femoral head, hip fracture, trochanter |
| `thigh_left` | Left Femur / Quadriceps Region | left thigh, femur, quadriceps, hamstring |
| `knee_left` | Left Patellofemoral / Tibiofemoral Joint | left knee, patella, meniscus, ACL, PCL, MCL, LCL |
| `lower_leg_left` | Left Tibia / Fibula Region | left lower leg, left shin, tibia, fibula, calf |
| `ankle_left` | Left Talocrural Joint | left ankle, talocrural, talus, ankle fracture, malleolus |
| `foot_left` | Left Foot (Metatarsals / Digits) | left foot, metatarsal, toe, foot fracture, calcaneus, heel |

### Right Lower Limb (6 regions)

| Region ID | Clinical Label | Common Terms |
|-----------|----------------|--------------|
| `hip_right` | Right Acetabulofemoral Joint | right hip, acetabulum, femoral head, hip fracture, trochanter |
| `thigh_right` | Right Femur / Quadriceps Region | right thigh, femur, quadriceps, hamstring |
| `knee_right` | Right Patellofemoral / Tibiofemoral Joint | right knee, patella, meniscus, ACL, PCL, MCL, LCL |
| `lower_leg_right` | Right Tibia / Fibula Region | right lower leg, right shin, tibia, fibula, calf |
| `ankle_right` | Right Talocrural Joint | right ankle, talocrural, talus, ankle fracture, malleolus |
| `foot_right` | Right Foot (Metatarsals / Digits) | right foot, metatarsal, toe, foot fracture, calcaneus, heel |

**Total: 32 anatomically distinct regions**

## SVG Requirements

### Front View (`body_front.svg`)

Must include these regions:
- All regions listed above EXCEPT: `thoracic_spine`, `lumbar_spine`, `sacroiliac`
- These spine regions appear only in back view for anatomical accuracy

### Back View (`body_back.svg`)

Must include these regions:
- All regions listed above
- Spine regions (`cervical_spine`, `thoracic_spine`, `lumbar_spine`, `sacroiliac`) are PRIMARY in back view

### SVG Structure

Each clickable region should be structured as:

```xml
<path id="region_id"
      fill="rgba(59, 130, 246, 0.2)"
      stroke="rgba(59, 130, 246, 0.5)"
      stroke-width="1"
      class="clickable-region"
      data-region="region_id"
      d="M ... path data ..."/>
```

Or using other shapes:

```xml
<ellipse id="region_id"
         cx="150" cy="40" rx="30" ry="35"
         fill="rgba(59, 130, 246, 0.2)"
         stroke="rgba(59, 130, 246, 0.5)"
         stroke-width="1"
         class="clickable-region"
         data-region="region_id"/>
```

### Important Attributes

1. **`id`**: Must exactly match region IDs from the table above
2. **`class="clickable-region"`**: Required for styling and interaction
3. **`data-region`**: Should match the `id` (used for data binding)
4. **Fill opacity**: Keep at 0.2-0.3 for subtlety
5. **Stroke opacity**: Keep at 0.4-0.6 for visibility

### CSS Classes Required

```css
.clickable-region {
  cursor: pointer;
  opacity: 0.3;
  transition: opacity 0.2s, fill 0.2s;
}

.clickable-region:hover {
  opacity: 0.7;
  fill: rgba(59, 130, 246, 0.4);
}

.clickable-region.selected {
  opacity: 1;
  fill: rgba(59, 130, 246, 0.6);
  stroke: rgb(59, 130, 246);
  stroke-width: 2;
}
```

## Editing SVGs in Inkscape

### 1. Open SVG in Inkscape

### 2. Draw Region Polygons

- Use Bezier Tool (B key)
- Trace anatomical boundaries
- Close the path

### 3. Set Region Properties

For each region:
1. Right-click → Object Properties
2. Set `id` to the region ID from tables above
3. Set `Label` to the clinical label

### 4. Set Fill/Stroke

- Fill: `rgba(59, 130, 246, 0.2)` (light blue, 20% opacity)
- Stroke: `rgba(59, 130, 246, 0.5)` (blue, 50% opacity)
- Stroke width: 1px

### 5. Add CSS Class

In XML Editor (Edit → XML Editor):
- Add attribute: `class="clickable-region"`
- Add attribute: `data-region="[region_id]"`

### 6. Save as Plain SVG

File → Save As → Plain SVG (not Inkscape SVG)

## Troubleshooting

### Region not clickable

- Check `id` matches exactly (case-sensitive)
- Verify `class="clickable-region"` is present
- Ensure region has fill (even if transparent)
- Check if another region overlaps

### Region not highlighted on hover

- Verify CSS is included in SVG
- Check fill opacity is not 0
- Ensure region is not hidden

### Wrong region selected

- Check for overlapping regions
- Verify `data-region` attribute matches `id`
- Ensure regions are in correct z-order (front to back)

## Customization

You can customize colors by editing:

1. **In SVG file** - change RGBA values
2. **In CSS** - modify `.clickable-region` styles
3. **In region_map.json** - adjust labels and terms

## Example: Adding a New Region

1. **Add to region_map.json:**
```json
"new_region_id": {
  "label": "Clinical Name",
  "compendium_terms": ["term1", "term2", ...]
}
```

2. **Add to SVG:**
```xml
<path id="new_region_id"
      fill="rgba(59, 130, 246, 0.2)"
      stroke="rgba(59, 130, 246, 0.5)"
      class="clickable-region"
      data-region="new_region_id"
      d="M ... "/>
```

3. **Update UI groupings** in `streamlit_app.py` if needed

## Best Practices

1. **Use clinical terminology** - matches legal documentation
2. **Be anatomically precise** - distinct regions improve search accuracy
3. **Avoid overlapping regions** - causes selection conflicts
4. **Test thoroughly** - verify all regions clickable and mappable
5. **Document custom regions** - maintain this reference guide

## License Note

The SVG body diagrams are part of this open-source project. You may modify and distribute them under the project license. If using external diagrams, ensure proper attribution and licensing.
