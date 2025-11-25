"""
Anatomical Structure Mappings
Maps specific bones, muscles, ligaments, and other structures to body regions
"""

# Comprehensive mapping of anatomical structures to region IDs
ANATOMICAL_MAPPINGS = {
    # Head & Skull
    "skull": ["head"],
    "cranium": ["head"],
    "cranial": ["head"],
    "facial": ["head"],
    "mandible": ["head"],
    "maxilla": ["head"],
    "zygomatic": ["head"],
    "temporal bone": ["head"],
    "orbital": ["head"],
    "nasal": ["head"],
    "brain": ["head"],
    "cerebral": ["head"],
    "cerebellum": ["head"],
    "frontal lobe": ["head"],
    "temporal lobe": ["head"],
    "parietal": ["head"],
    "occipital": ["head"],

    # Cervical Spine
    "c1": ["cervical_spine"],
    "c2": ["cervical_spine"],
    "c3": ["cervical_spine"],
    "c4": ["cervical_spine"],
    "c5": ["cervical_spine"],
    "c6": ["cervical_spine"],
    "c7": ["cervical_spine"],
    "atlas": ["cervical_spine"],
    "axis": ["cervical_spine"],
    "cervical vertebra": ["cervical_spine"],
    "cervical disc": ["cervical_spine"],
    "sternocleidomastoid": ["cervical_spine"],
    "trapezius": ["cervical_spine", "shoulder_left", "shoulder_right"],

    # Thoracic Spine
    "t1": ["thoracic_spine"],
    "t2": ["thoracic_spine"],
    "t3": ["thoracic_spine"],
    "t4": ["thoracic_spine"],
    "t5": ["thoracic_spine"],
    "t6": ["thoracic_spine"],
    "t7": ["thoracic_spine"],
    "t8": ["thoracic_spine"],
    "t9": ["thoracic_spine"],
    "t10": ["thoracic_spine"],
    "t11": ["thoracic_spine"],
    "t12": ["thoracic_spine"],
    "thoracic vertebra": ["thoracic_spine"],
    "thoracic disc": ["thoracic_spine"],

    # Lumbar Spine
    "l1": ["lumbar_spine"],
    "l2": ["lumbar_spine"],
    "l3": ["lumbar_spine"],
    "l4": ["lumbar_spine"],
    "l5": ["lumbar_spine"],
    "lumbar vertebra": ["lumbar_spine"],
    "lumbar disc": ["lumbar_spine"],

    # Sacrum & Coccyx
    "s1": ["sacroiliac"],
    "sacrum": ["sacroiliac"],
    "sacral": ["sacroiliac"],
    "coccyx": ["sacroiliac"],
    "tailbone": ["sacroiliac"],
    "sacroiliac joint": ["sacroiliac"],

    # Chest & Ribs
    "rib": ["chest"],
    "ribs": ["chest"],
    "sternum": ["chest"],
    "costal": ["chest"],
    "intercostal": ["chest"],
    "pectoralis": ["chest"],

    # Shoulder (bilateral structures)
    "shoulder": ["shoulder_left", "shoulder_right"],
    "clavicle": ["shoulder_left", "shoulder_right"],
    "scapula": ["shoulder_left", "shoulder_right"],
    "acromion": ["shoulder_left", "shoulder_right"],
    "coracoid": ["shoulder_left", "shoulder_right"],
    "glenoid": ["shoulder_left", "shoulder_right"],
    "rotator cuff": ["shoulder_left", "shoulder_right"],
    "supraspinatus": ["shoulder_left", "shoulder_right"],
    "infraspinatus": ["shoulder_left", "shoulder_right"],
    "teres minor": ["shoulder_left", "shoulder_right"],
    "subscapularis": ["shoulder_left", "shoulder_right"],
    "deltoid": ["shoulder_left", "shoulder_right"],
    "labrum": ["shoulder_left", "shoulder_right"],

    # Upper Arm
    "humerus": ["arm_left", "arm_right"],
    "humeral": ["arm_left", "arm_right"],
    "bicep": ["arm_left", "arm_right"],
    "biceps": ["arm_left", "arm_right"],
    "tricep": ["arm_left", "arm_right"],
    "triceps": ["arm_left", "arm_right"],
    "brachial": ["arm_left", "arm_right"],

    # Elbow
    "elbow": ["elbow_left", "elbow_right"],
    "olecranon": ["elbow_left", "elbow_right"],
    "radial head": ["elbow_left", "elbow_right"],
    "lateral epicondyle": ["elbow_left", "elbow_right"],
    "medial epicondyle": ["elbow_left", "elbow_right"],
    "ulnar collateral": ["elbow_left", "elbow_right"],

    # Forearm
    "radius": ["forearm_left", "forearm_right"],
    "radial": ["forearm_left", "forearm_right", "wrist_left", "wrist_right"],
    "ulna": ["forearm_left", "forearm_right"],
    "ulnar": ["forearm_left", "forearm_right", "wrist_left", "wrist_right"],

    # Wrist
    "wrist": ["wrist_left", "wrist_right"],
    "carpal": ["wrist_left", "wrist_right"],
    "scaphoid": ["wrist_left", "wrist_right"],
    "lunate": ["wrist_left", "wrist_right"],
    "triquetrum": ["wrist_left", "wrist_right"],
    "pisiform": ["wrist_left", "wrist_right"],
    "trapezium": ["wrist_left", "wrist_right"],
    "trapezoid": ["wrist_left", "wrist_right"],
    "capitate": ["wrist_left", "wrist_right"],
    "hamate": ["wrist_left", "wrist_right"],
    "tfcc": ["wrist_left", "wrist_right"],
    "radiocarpal": ["wrist_left", "wrist_right"],

    # Hand
    "hand": ["hand_left", "hand_right"],
    "metacarpal": ["hand_left", "hand_right"],
    "phalanx": ["hand_left", "hand_right"],
    "phalangeal": ["hand_left", "hand_right"],
    "thumb": ["hand_left", "hand_right"],
    "index finger": ["hand_left", "hand_right"],
    "middle finger": ["hand_left", "hand_right"],
    "ring finger": ["hand_left", "hand_right"],
    "pinky": ["hand_left", "hand_right"],
    "little finger": ["hand_left", "hand_right"],

    # Pelvis & Hip
    "pelvis": ["pelvis"],
    "pelvic": ["pelvis"],
    "hip": ["hip_left", "hip_right"],
    "ilium": ["pelvis", "hip_left", "hip_right"],
    "iliac": ["pelvis", "hip_left", "hip_right"],
    "pubis": ["pelvis"],
    "ischium": ["pelvis"],
    "acetabulum": ["hip_left", "hip_right"],
    "femoral head": ["hip_left", "hip_right"],
    "greater trochanter": ["hip_left", "hip_right"],
    "lesser trochanter": ["hip_left", "hip_right"],
    "hip joint": ["hip_left", "hip_right"],

    # Thigh
    "femur": ["thigh_left", "thigh_right"],
    "femoral": ["thigh_left", "thigh_right"],
    "quadriceps": ["thigh_left", "thigh_right"],
    "hamstring": ["thigh_left", "thigh_right"],
    "adductor": ["thigh_left", "thigh_right"],

    # Knee
    "knee": ["knee_left", "knee_right"],
    "patella": ["knee_left", "knee_right"],
    "patellar": ["knee_left", "knee_right"],
    "meniscus": ["knee_left", "knee_right"],
    "meniscal": ["knee_left", "knee_right"],
    "acl": ["knee_left", "knee_right"],
    "pcl": ["knee_left", "knee_right"],
    "mcl": ["knee_left", "knee_right"],
    "lcl": ["knee_left", "knee_right"],
    "anterior cruciate": ["knee_left", "knee_right"],
    "posterior cruciate": ["knee_left", "knee_right"],
    "medial collateral": ["knee_left", "knee_right"],
    "lateral collateral": ["knee_left", "knee_right"],
    "tibial plateau": ["knee_left", "knee_right"],

    # Lower Leg
    "tibia": ["lower_leg_left", "lower_leg_right"],
    "tibial": ["lower_leg_left", "lower_leg_right"],
    "fibula": ["lower_leg_left", "lower_leg_right"],
    "fibular": ["lower_leg_left", "lower_leg_right"],
    "shin": ["lower_leg_left", "lower_leg_right"],
    "calf": ["lower_leg_left", "lower_leg_right"],
    "gastrocnemius": ["lower_leg_left", "lower_leg_right"],
    "soleus": ["lower_leg_left", "lower_leg_right"],
    "achilles": ["lower_leg_left", "lower_leg_right", "ankle_left", "ankle_right"],

    # Ankle
    "ankle": ["ankle_left", "ankle_right"],
    "talus": ["ankle_left", "ankle_right"],
    "talar": ["ankle_left", "ankle_right"],
    "malleolus": ["ankle_left", "ankle_right"],
    "lateral malleolus": ["ankle_left", "ankle_right"],
    "medial malleolus": ["ankle_left", "ankle_right"],
    "ankle mortise": ["ankle_left", "ankle_right"],
    "deltoid ligament": ["ankle_left", "ankle_right"],
    "atfl": ["ankle_left", "ankle_right"],
    "anterior talofibular": ["ankle_left", "ankle_right"],

    # Foot
    "foot": ["foot_left", "foot_right"],
    "calcaneus": ["foot_left", "foot_right"],
    "calcaneal": ["foot_left", "foot_right"],
    "heel": ["foot_left", "foot_right"],
    "navicular": ["foot_left", "foot_right"],
    "cuboid": ["foot_left", "foot_right"],
    "cuneiform": ["foot_left", "foot_right"],
    "metatarsal": ["foot_left", "foot_right"],
    "toe": ["foot_left", "foot_right"],
    "toes": ["foot_left", "foot_right"],
    "plantar fascia": ["foot_left", "foot_right"],

    # General terms that need lateralization context
    "proximal": [],  # Requires context
    "distal": [],  # Requires context
    "medial": [],  # Requires context
    "lateral": [],  # Requires context
}

# Laterality indicators (removed single letter patterns to avoid false positives)
LATERALITY_LEFT = ["left", "lt", "lft", "sinister"]
LATERALITY_RIGHT = ["right", "rt", "rgt", "dextra"]
LATERALITY_BILATERAL = ["bilateral", "bilat", "b/l", "both"]


def map_anatomical_term_to_regions(term: str, context: str = "") -> list:
    """
    Map an anatomical term to body region IDs

    Args:
        term: Anatomical structure name (e.g., "tibia", "femur")
        context: Surrounding text for laterality detection

    Returns:
        List of region IDs that match this structure
    """
    term_lower = term.lower().strip()
    context_lower = context.lower()

    # Helper function to check laterality in a narrow window around the term
    def check_laterality_near_term(context_lower: str, term: str) -> tuple:
        """Check for laterality indicators near the term (within 30 chars before term)"""
        term_pos = context_lower.find(term)
        if term_pos == -1:
            # Term not in context, check full context (fallback)
            has_left = any(lat in context_lower for lat in LATERALITY_LEFT)
            has_right = any(lat in context_lower for lat in LATERALITY_RIGHT)
            has_bilateral = any(lat in context_lower for lat in LATERALITY_BILATERAL)
            return has_left, has_right, has_bilateral

        # Check narrow window before the term (30 chars)
        narrow_start = max(0, term_pos - 30)
        narrow_context = context_lower[narrow_start:term_pos + len(term) + 10]

        has_left = any(lat in narrow_context for lat in LATERALITY_LEFT)
        has_right = any(lat in narrow_context for lat in LATERALITY_RIGHT)
        has_bilateral = any(lat in narrow_context for lat in LATERALITY_BILATERAL)

        return has_left, has_right, has_bilateral

    # Direct lookup
    if term_lower in ANATOMICAL_MAPPINGS:
        regions = ANATOMICAL_MAPPINGS[term_lower]

        # If bilateral structure, try to determine laterality
        if len(regions) == 2 and "_left" in regions[0]:
            has_left, has_right, has_bilateral = check_laterality_near_term(context_lower, term_lower)

            if has_bilateral or (has_left and has_right):
                return regions  # Both sides
            elif has_left:
                return [r for r in regions if "_left" in r]
            elif has_right:
                return [r for r in regions if "_right" in r]
            else:
                return regions  # Unknown laterality, return both

        return regions

    # Partial matching for compound terms
    for key, regions in ANATOMICAL_MAPPINGS.items():
        if key in term_lower or term_lower in key:
            # Apply laterality detection for bilateral structures
            if len(regions) == 2 and "_left" in regions[0] and "_right" in regions[1]:
                has_left, has_right, has_bilateral = check_laterality_near_term(context_lower, key)

                if has_bilateral or (has_left and has_right):
                    return regions  # Both sides
                elif has_left:
                    return [r for r in regions if "_left" in r]
                elif has_right:
                    return [r for r in regions if "_right" in r]
                else:
                    return regions  # Unknown laterality, return both

            return regions

    return []


def enhance_region_detection(text: str, existing_regions: list = None) -> list:
    """
    Enhanced region detection using anatomical structure mapping

    Args:
        text: Medical report text
        existing_regions: Already detected regions (will be merged)

    Returns:
        List of detected region IDs
    """
    if existing_regions is None:
        existing_regions = []

    detected_regions = set(existing_regions)
    text_lower = text.lower()

    # Scan for anatomical terms
    for term, regions in ANATOMICAL_MAPPINGS.items():
        if term in text_lower:
            # Get context window around the term (increased to 100 chars for better laterality detection)
            term_index = text_lower.find(term)
            context_start = max(0, term_index - 100)
            context_end = min(len(text), term_index + len(term) + 100)
            context = text[context_start:context_end]

            # Map with laterality detection
            mapped_regions = map_anatomical_term_to_regions(term, context)
            detected_regions.update(mapped_regions)

    return list(detected_regions)
