"""Package the complete female movement and standing injury draft sets."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from verify_all import verify

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def write_named(archive, source, target, job):
    """Keep exported metadata connected after renaming a sheet."""
    if source.suffix != '.json':
        archive.write(source, target)
        return
    metadata = json.loads(source.read_text())
    metadata.update(id=job['id'], race=job['race'], sex='female', appearance=job['appearance'],
                    image=Path(target).with_suffix('.png').name,
                    dmi=Path(target).with_suffix('.dmi').name)
    archive.writestr(target, json.dumps(metadata, indent=2) + '\n')


def export():
    verify(require_complete=True)
    catalog = json.loads((HERE / 'all-catalog.json').read_text())
    sources = {j['id']: j for j in json.loads((HERE.parents[1] / 'female-animations/manifest.json').read_text())}
    destination = ROOT / 'Dungeon Master Sample/GOA Female Sprite Drafts.zip'
    records = []
    with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
        for job in catalog:
            folder = Path(job['folder'])
            name = job['race'].replace(' ', '-') + '-Female-' + job['appearance']
            prefix = job['race'] + '/' + job['appearance'] + '/'
            for suffix in ('.png', '.dmi', '.json'):
                write_named(archive, folder / ('injuries64-v1' + suffix), prefix + name + '-injuries' + suffix, job)
            archive.write(folder / 'reference.png', prefix + 'source/female-reference.png')
            for category in ('arms', 'legs'):
                path = Path(job['categories'][category]['path'])
                for suffix in ('.png', '.prompt.txt', '.json'):
                    source = path.with_suffix(suffix)
                    if source.exists():
                        archive.write(source, prefix + 'source/' + category + suffix)
                for extra in sorted(path.parent.glob(path.stem + '-*')):
                    if extra.is_file() and '.tmp.' not in extra.name:
                        archive.write(extra, prefix + 'source/' + extra.name)
            for path in sorted((folder / 'overrides').glob('*')):
                if path.is_file():
                    archive.write(path, prefix + 'source/overrides/' + path.name)
            for filename in ('combined-6rows-v1.png','combined-6rows-v1.json','combined-6rows-v1.prompt.txt'):
                source = folder / filename
                if source.exists():
                    archive.write(source, prefix + 'source/' + filename)
            female_source = Path(sources[job['id']]['folder'])
            for original, suffix in [('sprites.png', '-walk.png'), ('movement.dmi', '-walk.dmi'), ('atlas.json', '-walk.json')]:
                write_named(archive, female_source / original, prefix + name + suffix, job)
            for filename in ('prompt.txt', 'generation.json', 'correction-prompt.txt', 'correction-generation.json'):
                path = female_source / filename
                if path.exists():
                    archive.write(path, prefix + 'source/walk-' + filename)
            records.append(dict(id=job['id'], race=job['race'], sex='female', appearance=job['appearance'],
                                injuries=prefix+name+'-injuries.png', walk=prefix+name+'-walk.png',
                                injuriesDmi=prefix+name+'-injuries.dmi', walkDmi=prefix+name+'-walk.dmi',
                                injuriesMetadata=prefix+name+'-injuries.json', walkMetadata=prefix+name+'-walk.json'))
        for path in sorted((HERE / 'no-arms-repairs').glob('*')):
            if path.is_file() and path.suffix in ('.png','.json','.txt'):
                archive.write(path, 'source-no-arms-repairs/' + path.name)
        archive.writestr('coverage.json', json.dumps(records, indent=2) + '\n')
        archive.write(HERE / 'verification.json', 'standing-verification.json')
        archive.write(HERE.parents[1] / 'female-animations/playback-verification.json', 'walk-playback-verification.json')
        archive.writestr('README.md', '# Female sprite drafts\n\n80 appearances: ten races, each base plus seven hybrid forms. '
                        'All frames are 64×64. Direction columns: South, North, East, West.\n\n'
                        'Walk PNG: neutral, step A, step B rows; play 0,1,0,2 at 200 ms per phase. '
                        'Walk DMI contains the same four-phase sequence.\n\n'
                        'Injury PNG/DMI: Normal, NoLeftArm, NoRightArm, NoArms, NoLeftLeg, NoRightLeg, NoLegs. '
                        'Standing poses only. Injured walking, attacks, sleep, equipment fitting and live game integration remain separate work. '
                        'No detached limb-piece assets are included.\n\n'
                        'Artwork is direct native AI editing of each female identity. Packing uses whole poses, nearest-neighbor sampling and transparent-fragment cleanup. '
                        'Prompts, source sheets and complete corrective poses are included for review.\n')
    print(json.dumps(dict(appearances=len(records), output=str(destination), bytes=destination.stat().st_size)))


if __name__ == '__main__':
    export()
