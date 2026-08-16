### **Instructions for a New Tree Visualization**

**To:** The Engineering Team
**From:** [Your Name]
**Subject:** Update for the Code Generation Search Tree Visualization

**Goal:** We want to update our current tree visualization to match the hierarchical style shown in the research paper. The new design should clearly show the top-down growth of the tree and make it easy to spot high-performing branches.

Here are the key changes needed:

#### 1. Change the Layout to a Hierarchical Tree

*   **Current State:** We are using a "force-directed" layout, where nodes push and pull on each other like magnets. This is causing them to clump together.
*   **Required Change:** Please switch to a **top-down, hierarchical tree layout**. The root node should be at the very top, and each new generation of nodes should appear in a new layer below its parent.

#### 2. Use Simple, Sequential Node IDs

*   **Current State:** The nodes are labeled with long, hard-to-read unique IDs (e.g., `4bbec9`, `89ab...`).
*   **Required Change:** Instead of the long ID, please display a simple, sequential ID like `#1`, `#2`, `#3`, etc., based on the order the node was created. The root node can be labeled `#0`.

#### 3. Implement a Score-to-Color Gradient

*   **Current State:** We have different colors, but the meaning isn't as clear as it could be.
*   **Required Change:** Let's map the node's score to a color gradient. This will help us instantly see where the good solutions are.
    *   **Low-scoring nodes:** Purple
    *   **Mid-scoring nodes:** Blue
    *   **High-scoring nodes:** Teal or Green

#### 4. Simplify the Connecting Lines (Edges)

*   **Current State:** We have thick, colored lines with labels on them.
*   **Required Change:** All lines connecting a parent to a child should be simple, thin, grey lines with no labels. This will make the structure cleaner and easier to follow.

---
### Summary of Expected Result

The final visualization should look like a clean, top-down family tree. It should be immediately obvious which nodes are "children" of others, and the color gradient will guide our eyes to the most successful branches of the search.