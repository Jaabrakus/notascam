# Layered Deepguard fitting prototype

One approved Deepguard design, fitted onto three existing body shapes: human/standard, dwarf/stocky and goblin/small. The same twelve extracted pieces are grouped into eight independently switchable equipment slots. No new armor design is generated per race.

Each profile contains a transparent 256×64 base sheet, eight matching equipment sheets and a composed sheet plus four individual 64×64 equipped frames. Source pixels use nearest-neighbor anatomical fitting; source artwork is preserved. Body ears stay visible outside the helmet. The viewer allows slot toggling and per-facing pixel offsets; adjusted sheets and recipes can be exported.

The fit belongs to body shape, not crafting origin or sex. A hybrid or female body can reuse a profile when its anatomy matches; different proportions and horns/wings require a reviewed exception. Those variants are not demonstrated or validated here.

Standing South, North, East and West only. Hidden equipment surfaces, walking, holding poses, attacks and sixteen facings still require authored work. This does not establish universal fit for every body.

Rebuild with: python3 standalone/goa-races/layered-deepguard-v1/build.py
