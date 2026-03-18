from thefuzz import process
import os

def fuzzy_search(query, paths):
    query = query.lower()
    
    def match_score(name):
        name_lower = name.lower()
        score = 0
        q_idx = 0
        
        # Exact substring match bonus
        if query in name_lower:
            score += 100
            
        for char in name_lower:
            if q_idx < len(query) and char == query[q_idx]:
                q_idx += 1
                score += 1 # matched characters in order
        
        if q_idx == len(query):
            # All characters matched in order
            # The shorter the string, the better the match
            return score + (1000 / len(name))
        return 0
        
    results = []
    for p in paths:
        s = match_score(p.name)
        if s > 0:
            results.append((s, p))
            
    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)
    return [p for score, p in results]

