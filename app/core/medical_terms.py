"""
Medical term expansion dictionary for improved search matching.

This module provides semantic expansion of medical terms to improve search
results by matching related concepts, synonyms, and hierarchical relationships.
"""

from typing import List, Set

# Medical term expansion dictionary
# Maps search terms to related concepts that should also be matched
MEDICAL_TERM_EXPANSIONS = {
    # Brain injuries
    "brain damage": [
        "traumatic brain injury", "tbi", "brain injury", "head injury",
        "diffuse axonal injury", "dai", "cerebral contusion", "brain contusion",
        "intracranial hemorrhage", "subdural hematoma", "epidural hematoma",
        "subarachnoid hemorrhage", "brain hemorrhage", "concussion",
        "post-concussion syndrome", "cerebral edema", "brain swelling"
    ],
    "traumatic brain injury": [
        "tbi", "brain injury", "head injury", "brain damage",
        "diffuse axonal injury", "cerebral contusion", "concussion"
    ],
    "tbi": [
        "traumatic brain injury", "brain injury", "head injury", "brain damage"
    ],
    "diffuse axonal injury": [
        "dai", "brain damage", "traumatic brain injury", "tbi", "brain injury",
        "head injury", "shearing injury", "axonal injury"
    ],
    "dai": [
        "diffuse axonal injury", "brain damage", "traumatic brain injury", "brain injury"
    ],
    "concussion": [
        "brain injury", "mild traumatic brain injury", "mtbi", "head injury",
        "post-concussion syndrome", "brain trauma"
    ],
    "subdural hematoma": [
        "brain hemorrhage", "intracranial bleeding", "brain injury", "head injury"
    ],

    # Spinal injuries
    "spinal cord injury": [
        "sci", "spinal injury", "spine injury", "cord injury",
        "paraplegia", "quadriplegia", "tetraplegia", "paralysis",
        "spinal trauma", "vertebral fracture", "spinal fracture"
    ],
    "sci": [
        "spinal cord injury", "spinal injury", "spine injury"
    ],
    "paraplegia": [
        "paralysis", "spinal cord injury", "lower body paralysis", "sci"
    ],
    "quadriplegia": [
        "tetraplegia", "paralysis", "spinal cord injury", "four limb paralysis", "sci"
    ],

    # Neck injuries
    "whiplash": [
        "cervical strain", "neck strain", "cervical sprain", "neck sprain",
        "cervical soft tissue injury", "wad", "whiplash associated disorder",
        "neck injury", "cervical injury"
    ],
    "herniated disc": [
        "ruptured disc", "slipped disc", "disc herniation", "disc protrusion",
        "disc bulge", "protruding disc", "prolapsed disc", "disc displacement",
        "herniated disk", "ruptured disk"
    ],
    "ruptured disc": [
        "herniated disc", "slipped disc", "disc herniation", "disc rupture"
    ],
    "cervical radiculopathy": [
        "pinched nerve neck", "nerve compression neck", "cervical nerve root compression",
        "radiculopathy", "cervical neuropathy"
    ],

    # Back injuries
    "lumbar strain": [
        "lower back strain", "back strain", "lumbar sprain", "back sprain",
        "lumbar soft tissue injury", "low back pain"
    ],
    "lumbar radiculopathy": [
        "pinched nerve back", "sciatica", "nerve compression lumbar",
        "lumbar nerve root compression", "radiculopathy"
    ],
    "sciatica": [
        "lumbar radiculopathy", "sciatic nerve pain", "nerve pain leg",
        "radiculopathy", "nerve compression"
    ],

    # Fractures
    "fracture": [
        "broken bone", "bone break", "bone fracture", "break"
    ],
    "broken bone": [
        "fracture", "bone break", "bone fracture"
    ],
    "comminuted fracture": [
        "shattered bone", "multiple fragment fracture", "complex fracture"
    ],
    "compound fracture": [
        "open fracture", "fracture", "bone break"
    ],
    "compression fracture": [
        "vertebral compression fracture", "spinal fracture", "crush fracture"
    ],

    # Soft tissue injuries
    "ligament tear": [
        "ligament rupture", "torn ligament", "ligamentous injury",
        "sprain", "ligament damage"
    ],
    "tendon tear": [
        "tendon rupture", "torn tendon", "tendinous injury", "tendon damage"
    ],
    "muscle tear": [
        "muscle rupture", "torn muscle", "muscle strain", "muscle damage"
    ],
    "rotator cuff tear": [
        "rotator cuff rupture", "shoulder tear", "rotator cuff injury"
    ],

    # Joint injuries
    "meniscus tear": [
        "torn meniscus", "meniscal tear", "knee cartilage tear", "knee injury"
    ],
    "acl tear": [
        "anterior cruciate ligament tear", "torn acl", "acl rupture",
        "knee ligament injury"
    ],
    "pcl tear": [
        "posterior cruciate ligament tear", "torn pcl", "pcl rupture",
        "knee ligament injury"
    ],
    "mcl tear": [
        "medial collateral ligament tear", "torn mcl", "mcl rupture",
        "knee ligament injury"
    ],
    "lcl tear": [
        "lateral collateral ligament tear", "torn lcl", "lcl rupture",
        "knee ligament injury"
    ],

    # Pain syndromes
    "chronic pain": [
        "persistent pain", "long-term pain", "pain syndrome",
        "chronic pain syndrome", "intractable pain"
    ],
    "complex regional pain syndrome": [
        "crps", "reflex sympathetic dystrophy", "rsd", "chronic pain syndrome"
    ],
    "crps": [
        "complex regional pain syndrome", "reflex sympathetic dystrophy",
        "chronic pain syndrome"
    ],
    "fibromyalgia": [
        "chronic widespread pain", "fibromyalgia syndrome", "fms"
    ],

    # Psychological injuries
    "ptsd": [
        "post-traumatic stress disorder", "post traumatic stress",
        "trauma", "psychological trauma", "emotional trauma"
    ],
    "post-traumatic stress disorder": [
        "ptsd", "post traumatic stress", "trauma", "psychological trauma"
    ],
    "depression": [
        "major depressive disorder", "clinical depression", "mdd",
        "depressive disorder", "mood disorder"
    ],
    "anxiety": [
        "anxiety disorder", "generalized anxiety disorder", "gad",
        "panic disorder", "anxiety syndrome"
    ],

    # Burns
    "burn": [
        "burn injury", "thermal injury", "scald", "fire injury"
    ],
    "third degree burn": [
        "full thickness burn", "severe burn", "deep burn"
    ],
    "second degree burn": [
        "partial thickness burn", "moderate burn"
    ],

    # Amputation
    "amputation": [
        "limb loss", "loss of limb", "traumatic amputation",
        "surgical amputation", "dismemberment"
    ],

    # Vision injuries
    "vision loss": [
        "blindness", "visual impairment", "loss of sight", "eye injury",
        "ocular injury", "visual deficit"
    ],
    "blindness": [
        "vision loss", "loss of sight", "visual impairment", "complete vision loss"
    ],

    # Hearing injuries
    "hearing loss": [
        "deafness", "auditory impairment", "loss of hearing",
        "hearing impairment", "hearing deficit"
    ],
    "tinnitus": [
        "ringing in ears", "ear ringing", "auditory disorder"
    ],

    # Facial injuries
    "facial fracture": [
        "broken face", "face fracture", "facial bone fracture",
        "maxillofacial fracture", "jaw fracture", "cheekbone fracture",
        "orbital fracture", "nasal fracture"
    ],
    "jaw fracture": [
        "mandible fracture", "broken jaw", "facial fracture",
        "maxillary fracture"
    ],

    # Organ damage
    "kidney damage": [
        "renal injury", "kidney injury", "renal damage", "nephropathy"
    ],
    "liver damage": [
        "hepatic injury", "liver injury", "hepatic damage"
    ],
    "lung injury": [
        "pulmonary injury", "lung damage", "pulmonary contusion",
        "pneumothorax", "collapsed lung"
    ],

    # Internal injuries
    "internal bleeding": [
        "internal hemorrhage", "bleeding", "hemorrhage", "internal injury"
    ],
    "abdominal injury": [
        "abdominal trauma", "belly injury", "stomach injury",
        "internal injury", "blunt abdominal trauma"
    ],
}


def expand_query_terms(query: str) -> Set[str]:
    """
    Expand a query with related medical terms.

    Args:
        query: Original search query

    Returns:
        Set of expanded terms including original and related concepts
    """
    # Normalize query
    query_lower = query.lower().strip()

    # Start with original query terms
    expanded = {query_lower}

    # Split query into potential terms (handle comma-separated and phrases)
    # First try comma-separated
    potential_terms = [t.strip() for t in query_lower.split(',')]

    # Also try individual words for single word matches
    words = query_lower.split()
    potential_terms.extend(words)

    # Add multi-word phrases (bigrams, trigrams, etc.)
    for i in range(len(words)):
        for j in range(i + 2, min(i + 6, len(words) + 1)):
            potential_terms.append(' '.join(words[i:j]))

    # Find expansions for each term
    for term in potential_terms:
        term = term.strip()
        if term in MEDICAL_TERM_EXPANSIONS:
            expanded.update(MEDICAL_TERM_EXPANSIONS[term])
            # Also add the original term
            expanded.add(term)

    return expanded


def get_expanded_query_text(query: str) -> str:
    """
    Get expanded query text with medical synonyms for embedding.

    Args:
        query: Original search query

    Returns:
        Expanded query text with related medical terms
    """
    expanded_terms = expand_query_terms(query)

    # Combine original query with top expansions
    # Weight original query higher by including it multiple times
    result = f"{query}. {query}. "

    # Add expanded terms
    result += ". ".join(sorted(expanded_terms))

    return result


def get_keyword_expansion_terms(query: str) -> List[str]:
    """
    Get list of terms for keyword search expansion.

    Args:
        query: Original search query

    Returns:
        List of terms for keyword matching (includes original + expansions)
    """
    expanded_terms = expand_query_terms(query)
    return sorted(expanded_terms)
