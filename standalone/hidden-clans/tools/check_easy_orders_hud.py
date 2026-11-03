#!/usr/bin/env python3
"""Touch HUD rendering and request-contract checks in installed Chrome.

Only the byond URL transport is captured. This tests DOM/tap behavior at phone
widths; engine/native integration is tested separately by check_easy_orders_mouse.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / 'tests'


def check_live_unit_controls(browser, html, source_model, result):
    """Exercise task progress and item changes while the player has a control focused."""
    model = copy.deepcopy(source_model)
    unit = model['units'][0]
    unit.update(selected=True, paused=False, order='Chopping', job='woodcutter', autoUnload=True,
                items=[dict(ref='[0x21]', name='Wood', state='3 carried'),
                       dict(ref='[0x22]', name='Iron pickaxe', state='Equipped')])
    model.update(tab='units', selection=1, queue=True)
    model['settlement']['jobs'].append(dict(id='woodcutter', label='Woodcutter'))
    page = browser.new_page(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True)
    page.on('pageerror', lambda error: result['errors'].append(str(error)))
    page.set_content(html, wait_until='domcontentloaded')
    checks = result['checks']

    def render():
        page.evaluate('m=>updateHUD(m)', model)

    def request():
        return {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}

    def reset_request():
        page.evaluate("window.testLastURL='byond://?rm=unchanged'")

    render()
    pause = page.locator('#units [data-do=unitpause]')
    pause.focus()
    page.evaluate("window.savedPause=document.activeElement;window.savedStop=document.querySelector('#units [data-do=unitstop]')")
    unit['pending'].append(dict(ref='[0x13]', index=3, kind='Move', name='Grass', x=25, y=20, z=1))
    render()
    checks['queue_append_keeps_focused_pause_and_stop_controls'] = page.evaluate("savedPause===document.querySelector('#units [data-do=unitpause]')&&savedPause===document.activeElement&&savedStop===document.querySelector('#units [data-do=unitstop]')")
    unit.update(paused=True, order='Paused')
    render()
    checks['pause_status_is_not_duplicated_and_resume_keeps_focus'] = page.locator('#units .status').inner_text().count('Paused') == 1 and 'Role: Woodcutter' in page.locator('#units .status').inner_text() and page.evaluate("savedPause===document.querySelector('#units [data-do=unitresume]')&&savedPause===document.activeElement")

    # A pending task becomes active. The remaining remove button must keep its
    # own order reference while receiving its new ordinal, never its neighbor's.
    second = page.locator('#units [data-do=removeorder]').nth(1)
    second.focus()
    page.evaluate('window.savedPending=document.activeElement')
    unit['active'] = unit['pending'].pop(0)
    for i, task in enumerate(unit['pending'], 1): task['index'] = i
    render()
    checks['queue_progress_retains_focused_task_identity_and_new_ordinal'] = page.evaluate("savedPending===document.querySelector('#units [data-do=removeorder]')&&savedPending===document.activeElement&&savedPending.dataset.value==='[0x1]|1|[0x12]'")
    page.keyboard.press('Enter')
    checks['remove_after_queue_progress_targets_exact_surviving_order'] = request() == dict(rm='removeorder', value='[0x1]|1|[0x12]')
    reset_request()
    unit['pending'].pop(0)
    unit['pending'][0]['index'] = 1
    render()
    page.keyboard.press('Enter')
    checks['removed_focused_task_falls_back_to_description_without_command'] = page.locator('#units .currenttask').evaluate('e=>e===document.activeElement') and request() == dict(rm='unchanged') and page.locator('#units [data-do=removeorder]').get_attribute('data-value') == '[0x1]|1|[0x13]'

    details = page.locator('#units details').first
    details.evaluate('e=>e.open=true')
    item = page.locator('#units [data-do=inventory]').first
    item.focus()
    page.evaluate('window.savedItem=document.activeElement;window.savedDetails=document.activeElement.closest("details");window.savedScroll=scrollY')
    unit['items'][1]['state'] = 'Carried'
    render()
    checks['unrelated_item_update_preserves_open_inventory_focus_and_scroll'] = page.evaluate('savedItem===document.activeElement&&savedItem===document.querySelector("#units [data-do=inventory]")&&savedDetails===document.querySelector("#units details")&&savedDetails.open&&scrollY===savedScroll')
    unit['items'].pop(0)
    reset_request()
    render()
    checks['removed_inventory_item_focuses_its_summary_without_an_action'] = page.locator('#units summary').evaluate('e=>e===document.activeElement') and details.evaluate('e=>e.open') and request() == dict(rm='unchanged') and page.locator('#units [data-do=inventory]').get_attribute('data-value') == '[0x22]'
    page.locator('#units [data-do=inventory]').tap()
    checks['remaining_inventory_control_keeps_exact_item_request'] = request() == dict(rm='inventory', value='[0x22]')
    unit.update(items=[], pending=[], active=None, order='Idle', paused=False, job='manual', queued=0)
    render()
    checks['empty_inventory_and_queue_explain_next_action'] = 'No carried items' in page.locator('#units .inventoryhint').inner_text() and 'Click a destination or resource' in page.locator('#units .taskempty').inner_text()
    model['settlement']['stockpile'].update(filter='stone', accepts='stone')
    render()
    checks['auto_unload_hint_updates_for_stockpile_filter_without_unit_change'] = 'only accepted resources' in page.locator('#units .autohint').inner_text() and 'accepts stone' in page.locator('#units .autohint').inner_text()

    model['tab'] = 'orders'
    model['settlement']['stockpile']['set'] = False
    reset_request()
    render()
    page.locator('#dropOff').evaluate('e=>e.click()')
    page.locator('#unloadResume').evaluate('e=>e.click()')
    checks['missing_stockpile_disables_delivery_with_setup_reason'] = page.locator('#dropOff').is_disabled() and page.locator('#unloadResume').is_disabled() and 'Set a drop-off' in page.locator('#deliveryReason').inner_text() and page.locator('#deliverySetup').is_visible() and request() == dict(rm='unchanged')
    page.locator('#deliverySetup').tap()
    checks['delivery_setup_link_opens_existing_work_tab'] = request() == dict(rm='tab', value='work')
    model['settlement']['stockpile'].update(set=True, z=2)
    render()
    checks['different_level_delivery_explains_restriction'] = page.locator('#dropOff').is_disabled() and page.locator('#unloadResume').is_disabled() and 'level 2' in page.locator('#deliveryReason').inner_text()
    other = copy.deepcopy(unit)
    other.update(ref='[0x2]', name='Worker B', z=2)
    model['units'].append(other)
    model['selection'] = 2
    render()
    page.locator('#unloadResume').tap()
    checks['mixed_level_selection_delivers_eligible_units_and_explains_partial_group'] = not page.locator('#dropOff').is_disabled() and not page.locator('#unloadResume').is_disabled() and '1 of 2 selected units' in page.locator('#deliveryReason').inner_text() and request() == dict(rm='unloadresume', selection=model['controlGroups']['selection'])
    # Model changes after deselection carry the same unit's active work, but
    # expose no item controls and never emit Stop, Pause or Remove on their own.
    unit.update(active=dict(ref='[0x30]', kind='Chop', name='Oak', x=21, y=20, z=1), order='Chopping')
    render()
    page.locator('#deselect').tap()
    deselect_request = request()
    for current in model['units']: current['selected'] = False
    model.update(selection=0, queue=False)
    reset_request()
    render()
    checks['deselect_model_preserves_work_and_sends_no_cancellation'] = deselect_request == dict(rm='action', value='clear') and request() == dict(rm='unchanged') and 'Chopping' in page.locator('#units .status').first.text_content() and page.locator('#orderunits .card').count() == 0 and page.locator('#ordersEmpty').is_visible() and 'work continues' in page.locator('#ordersEmpty').inner_text()
    checks['no_selection_disables_delivery_with_selection_reason'] = page.locator('#dropOff').is_disabled() and page.locator('#unloadResume').is_disabled() and 'Select a unit' in page.locator('#deliveryReason').inner_text()
    unit['selected'] = True
    model.update(tab='units', selection=1)
    render()
    checks['reselect_preserves_inventory_expansion_and_active_work'] = details.evaluate('e=>e.open') and 'Chop · Oak' in page.locator('#units .currenttask').first.inner_text()

    # Long real-world names must wrap inside the cards at the narrowest width.
    unit['name'] = 'A very long worker name without truncating the important details'
    unit['items'] = [dict(ref='[0x41]', name='ExceptionallyLongEnchantedEquipmentName', state='Carried')]
    unit['pending'] = [dict(ref='[0x42]', index=1, kind='Mine', name='ExceptionallyLongRockTargetName', x=24, y=20, z=1)]
    page.set_viewport_size(dict(width=320, height=844))
    render()
    checks['live_unit_controls_wrap_and_remain_touch_sized_at_320'] = page.evaluate('document.documentElement.scrollWidth<=innerWidth') and page.locator('#units .card.selected .workbuttons button,#units .card.selected .taskrow button,#units .card.selected .inventory button').evaluate_all('els=>els.length===5&&els.every(e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth})')
    page.set_viewport_size(dict(width=390, height=844))
    page.locator('#units .currenttask').first.scroll_into_view_if_needed()
    page.screenshot(path=str(OUTPUT_DIR / 'hud-live-controls.png'))
    page.close()


def check_command_controls(page, browser, html, model, result):
    """Use the shipped catalog; every command is tapped at all three widths."""
    catalog = json.loads((ROOT / 'game/Interface/border-controls.json').read_text())
    groups = [dict(id=key, label=label) for key,label in (
        ('units','Units'), ('gather','Gather'), ('build','Build'),
        ('camera','Camera'), ('people','People'))]
    model['border'] = dict(visible=0, period='Day', groups=groups, controls=[dict(c,
        icon='remaster-border-' + c['id'] + '.png', reason='', active=0) for c in catalog])
    model['selection'] = 1
    model['units'][0]['selected'] = True
    page.evaluate('m=>updateHUD(m)', model)
    def request(target=page):
        return {key:values[0] for key,values in parse_qs(urlparse(target.evaluate('window.testLastURL')).query).items()}
    def untouched(target=page):
        return request(target) == dict(rm='unchanged')
    def reset_request(target=page):
        target.evaluate("window.testLastURL='byond://?rm=unchanged'")
    def visible_ids(target=page):
        return target.locator('#borderCatalog [data-control]:visible').evaluate_all('els=>els.map(e=>e.dataset.control)')
    def render():
        page.evaluate('m=>updateHUD(m)', model)
    checks = result['checks']
    core = page.locator('#quickDock [data-do=action]')
    checks['core_dock_has_labeled_stop_interact_and_goto'] = set(core.evaluate_all('els=>els.map(e=>e.dataset.value)')) == {'stop','interact','goto'} and core.evaluate_all('els=>els.every(e=>e.innerText.trim().length>2)')
    for action in ('stop','interact','goto'):
        page.locator('#quickDock [data-value='+action+']').tap()
        checks['core_dock_'+action+'_uses_existing_action'] = request() == dict(rm='action',value=action)
    model['selection'] = 0
    model['units'][0]['selected'] = False
    for control in model['border']['controls']:
        control['reason'] = 'Select a unit first' if control['needs_units'] else ''
    render()
    reset_request()
    checks['empty_selection_disables_core_dock_with_visible_reason'] = core.evaluate_all('els=>els.length===3&&els.every(e=>e.disabled&&e.getAttribute("aria-describedby"))') and 'Select a unit first' in page.locator('#dockHint').inner_text()
    core.evaluate_all('els=>els.forEach(e=>e.click())')
    checks['disabled_core_dock_never_sends_action'] = untouched()
    page.locator('#quickDock [data-ui=controls-open]').tap()
    checks['controls_open_is_local_and_keeps_classic_toggle_available'] = page.locator('#borderControls').evaluate('e=>e.open') and untouched() and page.locator('#borderVisibility').is_visible() and 'Show classic border' in page.locator('#borderVisibility').inner_text()
    disabled = next(c for c in catalog if c['needs_units'] and not c['indicator'])
    row = page.locator('[data-control='+disabled['id']+']')
    checks['unselected_catalog_command_has_disabled_button_and_reason'] = row.locator('[data-do=borderaction]').is_disabled() and 'Select a unit first' in row.locator('.reason').inner_text()
    row.locator('[data-do=borderaction]').evaluate('e=>e.click()')
    checks['disabled_catalog_command_never_sends_action'] = untouched()
    model['selection'] = 1
    model['units'][0]['selected'] = True
    for control in model['border']['controls']: control['reason'] = ''
    render()
    checks['purpose_groups_cover_every_catalog_row_once'] = set(page.locator('#borderCatalog .controlgroup').evaluate_all('els=>els.map(e=>e.dataset.group)')) == {g['id'] for g in groups} and set(visible_ids()) == {c['id'] for c in catalog} and len(visible_ids()) == 45
    checks['indicator_never_exposes_command'] = page.locator('[data-control=daynight] [data-do]').count() == 0
    reset_request()
    for group in groups:
        page.locator('#borderFilters [data-group='+group['id']+']').tap()
        expected = {c['id'] for c in catalog if c['group'] == group['id']}
        checks['purpose_filter_'+group['id']+'_is_complete_and_local'] = set(visible_ids()) == expected and untouched()
    page.locator('#borderFilters [data-group=all]').tap()
    search = page.locator('#controlSearch')
    search.fill('wood')
    found = visible_ids()
    checks['search_filters_matching_commands_without_actions'] = bool(found) and len(found) < 45 and all('wood' in page.locator('[data-control='+key+']').inner_text().lower() for key in found) and untouched()
    search.fill('zz-no-such-game-command-93929')
    checks['empty_search_has_no_action_rows_and_explains_result'] = not visible_ids() and page.locator('#controlsEmpty').is_visible() and bool(page.locator('#controlsEmpty').inner_text().strip()) and untouched()
    search.focus()
    page.keyboard.press('Enter')
    checks['enter_on_empty_search_does_not_fire_game_action'] = untouched()
    page.locator('#clearControlSearch').tap()
    checks['clear_search_restores_all_commands_without_action'] = search.input_value() == '' and len(visible_ids()) == 45 and untouched()
    search.fill('wood')
    search.focus()
    page.evaluate('window.savedControlSearch=document.querySelector("#controlSearch")')
    model['notice'] = 'A worker is still chopping'
    render()
    checks['hud_refresh_keeps_search_value_element_and_focus'] = page.evaluate('document.querySelector("#controlSearch")===window.savedControlSearch&&document.activeElement===window.savedControlSearch') and search.input_value() == 'wood'
    page.keyboard.press('Escape')
    checks['escape_from_search_closes_locally_and_restores_opener_focus'] = not page.locator('#borderControls').evaluate('e=>e.open') and untouched() and page.locator('#quickDock [data-ui=controls-open]').evaluate('e=>e===document.activeElement')
    page.locator('#commandCategories [data-group=build]').tap()
    checks['build_category_opens_matching_group_without_game_action'] = page.locator('#borderControls').evaluate('e=>e.open') and set(visible_ids()) == {c['id'] for c in catalog if c['group']=='build'} and untouched()
    page.locator('[data-ui=controls-close]').tap()
    checks['touch_close_returns_focus_to_category_opener'] = not page.locator('#borderControls').evaluate('e=>e.open') and page.locator('#commandCategories [data-group=build]').evaluate('e=>e===document.activeElement') and untouched()
    page.locator('#quickDock [data-ui=controls-open]').tap()
    page.locator('#borderFilters [data-group=all]').tap()
    page.locator('#borderVisibility').tap()
    checks['classic_border_can_be_restored_from_hidden_default'] = request() == dict(rm='border',value='show')
    model['border']['visible'] = 1
    render()
    page.locator('#borderVisibility').tap()
    checks['classic_border_hide_requests_explicit_state'] = request() == dict(rm='border',value='hide') and 'Hide classic border' in page.locator('#borderVisibility').inner_text()
    model['border']['visible'] = 0
    render()

    def icon_route(route):
        name = urlparse(route.request.url).path.removeprefix('/remaster-border-')
        path = ROOT / 'game/Interface/border-icons' / name
        if path.parent == ROOT / 'game/Interface/border-icons' and path.is_file(): route.fulfill(path=path,content_type='image/png')
        else: route.abort()
    # Every original command must remain reachable and send its exact catalog
    # ID, including commands below the fold in the narrow phone drawer.
    for width in (320,390,768):
        preview = browser.new_page(viewport=dict(width=width,height=844),is_mobile=True,has_touch=True)
        preview.on('pageerror',lambda error:result['errors'].append(str(error)))
        preview.route('http://hud.test/',lambda route:route.fulfill(body=html,content_type='text/html'))
        preview.route('http://hud.test/remaster-border-*.png',icon_route)
        preview.goto('http://hud.test/',wait_until='domcontentloaded')
        preview.evaluate('m=>updateHUD(m)',model)
        checks[f'camera_overview_starts_collapsed_with_world_status_visible_{width}'] = not preview.locator('#cameraOverview').evaluate('e=>e.open') and not preview.locator('#minimap').is_visible() and preview.locator('#worldDayIcon').is_visible() and preview.locator('#season').is_visible() and preview.locator('#coords').is_visible()
        preview.locator('#cameraOverview summary').tap()
        checks[f'camera_overview_expands_to_original_minimap_{width}'] = preview.locator('#cameraOverview').evaluate('e=>e.open') and preview.locator('#minimap').is_visible()
        preview.locator('#cameraOverview summary').tap()
        checks[f'core_dock_touch_targets_fit_{width}'] = preview.locator('#quickDock button').evaluate_all('els=>els.every(e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth})')
        checks[f'category_touch_targets_fit_{width}'] = preview.locator('#commandCategories button').evaluate_all('els=>els.every(e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth})')
        preview.locator('#quickDock [data-ui=controls-open]').tap()
        preview.wait_for_function('Array.from(document.querySelectorAll("#borderCatalog img")).every(i=>i.complete&&i.naturalWidth===32&&i.naturalHeight===32)')
        action_rows = [c for c in catalog if not c['indicator']]
        checks[f'all44_actions_visible_in_full_catalog_{width}'] = preview.locator('#borderCatalog [data-do=borderaction]').count()==44 and set(visible_ids(preview))=={c['id'] for c in catalog}
        exact = True
        touch = True
        closes = True
        batch = True
        close_ids = {'build','digpaint','digadd','digremove','interact','goto','warp','waypoint','coords','msg','say','race','updates','zup','zdown','all','area'}
        for control in action_rows:
            if not preview.locator('#borderControls').evaluate('e=>e.open'):
                preview.locator('#quickDock [data-ui=controls-open]').tap()
            button = preview.locator('#borderCatalog [data-do=borderaction][data-value='+control['id']+']')
            button.scroll_into_view_if_needed()
            touch &= button.evaluate('e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth}')
            button.tap()
            exact &= request(preview)==dict(rm='borderaction',value=control['id'])
            is_open = preview.locator('#borderControls').evaluate('e=>e.open')
            if control['id'] in close_ids: closes &= not is_open
            else: batch &= is_open
        if not preview.locator('#borderControls').evaluate('e=>e.open'):
            preview.locator('#quickDock [data-ui=controls-open]').tap()
        checks[f'all44_commands_tap_exact_catalog_id_{width}'] = exact
        checks[f'placement_prompt_and_camera_commands_return_to_map_{width}'] = closes
        checks[f'gather_equipment_commands_keep_drawer_open_for_repeated_use_{width}'] = batch
        checks[f'all44_command_touch_targets_fit_{width}'] = touch
        checks[f'full_command_drawer_fits_{width}'] = preview.locator('#borderControls').evaluate('e=>{const r=e.getBoundingClientRect(),b=e.querySelector(".drawerbody");return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight&&b.scrollWidth<=b.clientWidth}')
        checks[f'drawer_close_remains_visible_{width}'] = preview.locator('[data-ui=controls-close]').evaluate('e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.width>=44&&r.height>=44}')
        for variant in ('sun','moon'):
            day = next(c for c in model['border']['controls'] if c['id']=='daynight')
            day['icon']='remaster-border-daynight-'+variant+'.png'
            model['border']['period']='Day' if variant=='sun' else 'Night'
            preview.evaluate('m=>updateHUD(m)',model)
            preview.wait_for_function('document.querySelector("[data-control=daynight] img").complete&&document.querySelector("[data-control=daynight] img").naturalWidth===32')
            checks[f'daynight_{variant}_thumbnail_loads_{width}'] = preview.locator('[data-control=daynight] img').evaluate('e=>e.naturalWidth===32&&e.naturalHeight===32')
            checks[f'world_status_uses_current_{variant}_thumbnail_{width}'] = preview.locator('#worldDayIcon').get_attribute('src')==day['icon'] and model['border']['period'] in preview.locator('#season').inner_text()
        if width==390:
            preview.locator('#borderControls .drawerbody').evaluate('e=>e.scrollTop=0')
            preview.screenshot(path=str(OUTPUT_DIR / 'border-controls-hud.png'))
            preview.locator('[data-ui=controls-close]').tap()
            preview.evaluate('window.scrollTo(0,0)')
            preview.screenshot(path=str(OUTPUT_DIR / 'command-dock-hud.png'))
        preview.close()


def check_original_palette(browser, html, source_model, result):
    """Live menu tokens are opaque; changing menus must never retarget a button."""
    model = copy.deepcopy(source_model)
    model.update(tab='units', selection=1)
    model['units'][0]['selected'] = True
    model['palette'] = dict(open=False, entries=[], title='Build & abilities')
    page = browser.new_page(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True)
    page.on('pageerror', lambda error: result['errors'].append(str(error)))
    page.route('http://hud.test/', lambda route: route.fulfill(body=html, content_type='text/html'))
    page.route('http://hud.test/remaster-palette-present.png', lambda route: route.fulfill(path=ROOT/'game/Interface/border-icons/build.png', content_type='image/png'))
    page.route('http://hud.test/remaster-palette-missing.png', lambda route: route.fulfill(status=404, body=''))
    page.route('http://hud.test/remaster-border-*.png', lambda route: route.fulfill(path=ROOT/'game/Interface/border-icons/build.png', content_type='image/png'))
    page.goto('http://hud.test/', wait_until='domcontentloaded')
    checks = result['checks']

    def render():
        page.evaluate('m=>updateHUD(m)', model)

    def reset_request():
        page.evaluate("window.testLastURL='byond://?rm=unchanged';window.paletteRequests=[]")

    def request():
        return {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}

    page.evaluate("window.paletteRequests=[];let capturedURL=window.testLastURL;Object.defineProperty(window,'testLastURL',{configurable:true,get:()=>capturedURL,set:value=>{capturedURL=value;window.paletteRequests.push(value)}})")
    render()
    checks['palette_stays_closed_without_live_original_menu'] = not page.locator('#buildPalette').evaluate('e=>e.open') and page.locator('#paletteChoices button').count() == 0
    page.locator('#commandCategories [data-group=build]').tap()
    model['palette'] = dict(open=True, title='Build & abilities', entries=[
        dict(ref='palette-1', label='Wooden wall', icon='remaster-palette-present.png', reason=''),
        dict(ref='palette-2', label='Original ability', icon='remaster-palette-missing.png', reason=''),
        dict(ref='palette-3', label='Option without an icon', icon='', reason='')])
    reset_request()
    render()
    checks['live_palette_replaces_controls_without_sending_game_action'] = page.locator('#buildPalette').evaluate('e=>e.open') and not page.locator('#borderControls').evaluate('e=>e.open') and page.locator('#paletteTitle').evaluate('e=>e===document.activeElement') and request() == dict(rm='unchanged')
    page.wait_for_function('document.querySelector("#paletteChoices img").classList.contains("loaded")')
    page.wait_for_function('document.querySelectorAll("#paletteChoices img")[1].complete')
    checks['palette_uses_original_icon_and_hides_missing_icon_placeholders'] = page.locator('#paletteChoices img').first.get_attribute('src') == 'remaster-palette-present.png' and page.locator('#paletteChoices img').evaluate_all('els=>getComputedStyle(els[0]).visibility==="visible"&&els.slice(1).every(e=>getComputedStyle(e).visibility==="hidden")')
    reset_request()
    page.locator('#paletteChoices [data-value=palette-1]').tap()
    checks['palette_tap_sends_exact_opaque_token_once'] = request() == dict(rm='palette', value='palette-1') and page.evaluate('paletteRequests.length') == 1
    focused = page.locator('#paletteChoices [data-value=palette-1]')
    focused.focus()
    page.evaluate('window.savedPaletteChoice=document.activeElement')
    model['notice'] = 'World continues to update'
    model['palette']['entries'][1]['label'] = 'Updated original ability'
    render()
    checks['live_menu_update_preserves_focused_choice_token'] = page.evaluate('savedPaletteChoice===document.activeElement&&savedPaletteChoice.dataset.value==="palette-1"')
    model['palette']['entries'] = [dict(ref='palette-4', label='Original submenu choice', icon='remaster-palette-present.png', reason='')]
    reset_request()
    render()
    page.keyboard.press('Enter')
    checks['submenu_replacement_removes_stale_tokens_and_focuses_heading'] = page.locator('#paletteChoices [data-value=palette-1]').count() == 0 and page.locator('#paletteChoices [data-value=palette-4]').count() == 1 and page.locator('#paletteTitle').evaluate('e=>e===document.activeElement') and request() == dict(rm='unchanged')
    page.locator('#paletteChoices button').focus()
    model['palette']['entries'][0]['reason'] = 'Selection changed; reopen the menu for these units.'
    render()
    page.locator('#paletteChoices button').evaluate('e=>e.click()')
    checks['stale_selection_disables_choices_with_reason_and_safe_focus'] = page.locator('#paletteChoices button').is_disabled() and 'Selection changed' in page.locator('#paletteChoices button small').inner_text() and page.locator('#paletteRecovery').is_visible() and 'Build & terrain' in page.locator('#paletteRecovery').inner_text() and page.locator('#paletteTitle').evaluate('e=>e===document.activeElement') and request() == dict(rm='unchanged')
    reset_request()
    page.keyboard.press('Escape')
    checks['palette_escape_closes_menu_without_deselecting_or_canceling_tasks'] = not page.locator('#buildPalette').evaluate('e=>e.open') and request() == dict(rm='paletteclose') and page.locator('#commandCategories [data-group=build]').evaluate('e=>e===document.activeElement')
    render()
    checks['closed_palette_does_not_reopen_on_same_pending_snapshot'] = not page.locator('#buildPalette').evaluate('e=>e.open')
    model['palette'] = dict(open=False, entries=[], title='Build & abilities')
    render()
    model['palette'] = dict(open=True, title='Build & abilities', entries=[
        dict(ref='palette-'+str(i), label='Original building option '+str(i), icon='remaster-palette-present.png', reason='') for i in range(5,25)])
    render()
    # Long menus scroll internally. Close and all options stay usable at phone
    # widths without changing original recipes or replacing their game dialogs.
    fits = True
    for width in (320,390,768):
        page.set_viewport_size(dict(width=width, height=844))
        page.locator('#buildPalette .drawerbody').evaluate('e=>e.scrollTop=e.scrollHeight')
        fits &= page.locator('#buildPalette').evaluate('e=>{const r=e.getBoundingClientRect(),b=e.querySelector(".drawerbody");return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight&&b.scrollWidth<=b.clientWidth}')
        fits &= page.locator('#buildPalette [data-ui=palette-close]').evaluate('e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.width>=44&&r.height>=44}')
        fits &= page.locator('#paletteChoices button').evaluate_all('els=>els.every(e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth})')
    checks['long_palette_scrolls_inside_touch_sized_dialog_at_320_390_768'] = fits
    page.set_viewport_size(dict(width=390, height=844))
    page.locator('#buildPalette .drawerbody').evaluate('e=>e.scrollTop=0')
    page.screenshot(path=str(OUTPUT_DIR / 'original-palette-hud.png'))
    reset_request()
    page.locator('#buildPalette [data-ui=palette-close]').tap()
    checks['palette_close_button_requests_only_menu_close'] = request() == dict(rm='paletteclose') and not page.locator('#buildPalette').evaluate('e=>e.open')
    model['palette'] = dict(open=True, title='', entries=[dict(ref='palette-new', label='New menu choice', icon='', reason='')])
    render()
    checks['new_palette_can_open_after_close_with_fallback_title'] = page.locator('#buildPalette').evaluate('e=>e.open') and page.locator('#paletteTitle').inner_text() == 'Build & abilities'
    model['palette'].update(entries=[])
    render()
    checks['empty_original_menu_closes_and_clears_palette'] = not page.locator('#buildPalette').evaluate('e=>e.open') and page.locator('#paletteChoices button').count() == 0
    page.close()


def check_portraits(browser, html, source_model, result):
    """Failed or absent resources retain a usable unit card and a neutral frame."""
    model = copy.deepcopy(source_model)
    unit = model['units'][0]
    unit.update(selected=True, portrait='', name='Worker A')
    model.update(tab='units', selection=1)
    model.pop('palette', None)
    page = browser.new_page(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True)
    page.on('pageerror', lambda error: result['errors'].append(str(error)))
    requests = []
    page.on('request', lambda request: requests.append((request.resource_type, request.url)))
    page.route('http://hud.test/', lambda route: route.fulfill(body=html, content_type='text/html'))
    page.route('http://hud.test/portrait-valid.png', lambda route: route.fulfill(path=ROOT/'game/Interface/border-icons/build.png', content_type='image/png'))
    page.route('http://hud.test/portrait-missing.png', lambda route: route.fulfill(status=404, body=''))
    page.goto('http://hud.test/', wait_until='domcontentloaded')
    checks = result['checks']

    def render():
        page.evaluate('m=>updateHUD(m)', model)

    render()
    image = page.locator('#units .portraitimage').first
    fallback = page.locator('#units .portraitfallback').first
    checks['empty_portrait_uses_initials_without_empty_image_request'] = image.get_attribute('src') is None and fallback.is_visible() and fallback.inner_text() == 'WA' and not any(kind == 'image' and url == 'http://hud.test/' for kind,url in requests)
    page.locator('#units .unitpick').first.focus()
    page.evaluate('window.savedPortraitCard=document.querySelector("#units .card");window.savedPortraitPick=document.activeElement;window.savedPortraitImage=document.querySelector("#units .portraitimage")')
    unit['portrait'] = 'portrait-valid.png'
    render()
    page.wait_for_function('document.querySelector("#units .portraitimage").classList.contains("loaded")')
    checks['valid_portrait_replaces_fallback_without_replacing_card_or_focus'] = image.evaluate('e=>e.naturalWidth>0&&getComputedStyle(e).visibility==="visible"') and not fallback.is_visible() and page.evaluate('savedPortraitCard===document.querySelector("#units .card")&&savedPortraitPick===document.activeElement&&savedPortraitImage===document.querySelector("#units .portraitimage")')
    unit['portrait'] = 'portrait-missing.png'
    render()
    page.wait_for_function('document.querySelector("#units .portraitimage").complete')
    checks['failed_portrait_uses_fallback_and_keeps_selection_control'] = fallback.is_visible() and image.evaluate('e=>e.naturalWidth===0&&getComputedStyle(e).visibility==="hidden"') and page.evaluate('savedPortraitCard===document.querySelector("#units .card")&&savedPortraitPick===document.activeElement')
    page.locator('#units .unitpick').first.tap()
    request = {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}
    checks['portrait_failure_does_not_change_unit_selection_request'] = request == dict(rm='select', value=unit['ref'])
    unit['portrait'] = 'portrait-valid.png'
    render()
    page.wait_for_function('document.querySelector("#units .portraitimage").classList.contains("loaded")')
    loaded_again = image.evaluate('e=>e.naturalWidth>0&&getComputedStyle(e).visibility==="visible"') and not fallback.is_visible()
    unit.update(portrait='', name='New Name')
    render()
    checks['portrait_recovers_from_failure_and_can_return_to_named_fallback'] = loaded_again and image.get_attribute('src') is None and fallback.is_visible() and fallback.inner_text() == 'NN' and page.evaluate('savedPortraitCard===document.querySelector("#units .card")')
    page.locator('#units .unitpick').first.scroll_into_view_if_needed()
    page.screenshot(path=str(OUTPUT_DIR / 'hud-portrait-fallback.png'))
    page.close()


def finish_result(result, filename='easy-orders-hud-checks.json'):
    result['source_files_stable'] = result['html_sha256'] == hashlib.sha256((ROOT / 'game/Interface/remastered.html').read_bytes()).hexdigest() and result['catalog_sha256'] == hashlib.sha256((ROOT / 'game/Interface/border-controls.json').read_bytes()).hexdigest()
    result['passed'] = all(result['checks'].values()) and not result['errors'] and result['source_files_stable']
    (OUTPUT_DIR / filename).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


def check_mental_action(browser, html, source_model, result):
    model=copy.deepcopy(source_model)
    model.update(tab='work',selection=1)
    model['units'][0].update(selected=True,race='Illithid')
    command=dict(id='mental',label='Illithid mental abilities',key='F6',reason='Select an Illithid unit first.')
    model['commands']=[command]
    page=browser.new_page(viewport=dict(width=390,height=844),is_mobile=True,has_touch=True)
    page.on('pageerror',lambda error:result['errors'].append(str(error)))
    page.set_content(html,wait_until='domcontentloaded')
    checks=result['checks']

    def render():
        page.evaluate('m=>updateHUD(m)',model)

    def request():
        return {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}

    reasons=['Select an Illithid unit first.','Every selected unit must have Illithid mental abilities.','Leave mist form before using mental abilities.','Select your own living units.']
    rejected=True
    for reason in reasons:
        command['reason']=reason
        render()
        page.evaluate("window.testLastURL='byond://?rm=unchanged'")
        page.locator('#mentalAbilities').evaluate('e=>e.click()')
        page.locator('#commands [data-value=mental]').evaluate('e=>e.click()')
        rejected &= page.locator('#mentalAbilities').is_disabled() and page.locator('#mentalReason').inner_text()==reason and page.locator('#commands [data-value=mental]').is_disabled() and request()==dict(rm='unchanged')
    checks['mental_action_explains_and_blocks_server_reported_ineligibility_in_both_places']=rejected
    command['reason']=''
    render()
    page.locator('#mentalAbilities').tap()
    checks['mental_work_button_sends_original_action_id']=request()==dict(rm='action',value='mental') and 'F6' in page.locator('#mentalAbilities').inner_text()
    page.locator('#mentalAbilities').focus()
    page.evaluate('window.savedMentalButton=document.activeElement')
    model['notice']='Unit status updated'
    render()
    checks['mental_work_button_keeps_focus_during_world_update']=page.evaluate('savedMentalButton===document.querySelector("#mentalAbilities")&&savedMentalButton===document.activeElement')
    model['tab']='orders'
    render()
    page.locator('#page-orders details').evaluate('e=>e.open=true')
    page.locator('#commands [data-value=mental]').tap()
    checks['mental_action_remains_available_in_all_commands_with_f6']=request()==dict(rm='action',value='mental') and page.locator('#commands [data-value=mental] kbd').inner_text()=='F6'
    model['tab']='work'
    render()
    fits=True
    for width in (320,390,768):
        page.set_viewport_size(dict(width=width,height=844))
        fits &= page.locator('#mentalAbilities').evaluate('e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth&&document.documentElement.scrollWidth<=innerWidth}')
    checks['mental_touch_opener_fits_320_390_768']=fits
    page.close()


def check_compact_layout(browser, html, source_model, result):
    model = copy.deepcopy(source_model)
    model.update(tab='units', selection=1, idle=1, alert=0, notice='Ready')
    model['units'][0]['selected'] = True
    for width, height in ((320,568),(390,625),(768,844)):
        page = browser.new_page(viewport=dict(width=width,height=height),is_mobile=True,has_touch=True)
        page.on('pageerror', lambda error: result['errors'].append(str(error)))
        page.set_content(html, wait_until='domcontentloaded')
        page.evaluate('m=>updateHUD(m)',model)
        result['checks'][f'first_unit_name_and_portrait_visible_without_scrolling_{width}_{height}'] = page.locator('#units .unitpick').first.evaluate('e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight}')
        result['checks'][f'quick_actions_remain_visible_and_touch_sized_{width}_{height}'] = page.locator('#quickDock button,#deselect').evaluate_all('els=>els.every(e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.top>=0&&r.bottom<=innerHeight})')
        result['checks'][f'no_horizontal_overflow_short_screen_{width}_{height}'] = page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if width==390: page.screenshot(path=str(OUTPUT_DIR / 'hud-compact.png'))
        page.locator('#quickDock [data-ui=controls-open]').tap()
        result['checks'][f'all_controls_accessible_when_category_strip_hidden_{width}_{height}'] = page.locator('#borderControls').evaluate('e=>e.open') and page.locator('#borderControls [data-ui=controls-close]').evaluate('e=>e.getBoundingClientRect().bottom<=innerHeight')
        page.keyboard.press('Escape')
        page.locator('#cameraOverview summary').tap()
        result['checks'][f'camera_still_expands_without_command_{width}_{height}'] = page.locator('#minimap').is_visible()
        page.locator('#cameraOverview summary').tap()
        model['alert']=1
        page.evaluate('m=>updateHUD(m)',model)
        result['checks'][f'active_attack_alert_is_visible_without_opening_camera_{width}_{height}'] = page.locator('#attack').is_visible() and not page.locator('#attack').is_disabled()
        model['alert']=0
        page.close()


def check_magic_target(browser, html, source_model, result):
    """Touch chooser identity/focus contracts; game validation runs separately."""
    model=copy.deepcopy(source_model)
    model.update(tab='work',selection=1)
    command=dict(id='magictarget',label='Choose magic target',key='',reason='Select a unit first.')
    other=dict(id='mental',label='Mental abilities',key='F6',reason='')
    model['commands']=[command,other]
    page=browser.new_page(viewport=dict(width=390,height=625),is_mobile=True,has_touch=True)
    page.on('pageerror',lambda error:result['errors'].append(str(error)))
    page.set_content(html,wait_until='domcontentloaded')
    page.evaluate("window.magicRequests=[];let capturedMagicURL='';Object.defineProperty(window,'testLastURL',{configurable:true,get:()=>capturedMagicURL,set:value=>{capturedMagicURL=value;window.magicRequests.push(value)}})")
    checks=result['checks']

    def render():
        page.evaluate('m=>updateHUD(m)',model)

    def reset():
        page.evaluate("window.testLastURL='byond://?rm=unchanged';window.magicRequests=[]")

    def request():
        return {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}

    render()
    reset()
    page.locator('#magicTargetOpener').evaluate('e=>e.click()')
    checks['magic_target_unavailable_opener_explains_and_blocks']=page.locator('#magicTargetOpener').is_disabled() and page.locator('#magicTargetReason').inner_text()==command['reason'] and request()==dict(rm='unchanged')
    command['reason']=''
    render()
    page.locator('#magicTargetOpener').tap()
    checks['magic_target_touch_opener_sends_only_open_command']=request()==dict(rm='action',value='magictarget') and page.evaluate('magicRequests.length')==1
    model['magicTarget']=dict(open=True,session='session-A',reason='',actors=['Worker A'],entries=[
        dict(ref='target-1',label='<img src=x onerror=alert(1)>',race='Human',x=20,y=20,z=1,reason=''),
        dict(ref='target-2',label='Friendly healer',race='Elf',x=21,y=20,z=1,reason='')])
    reset()
    render()
    checks['magic_target_open_focuses_heading_without_issuing_orders']=page.locator('#magicTargets').evaluate('e=>e.open') and page.locator('#magicTargetTitle').evaluate('e=>e===document.activeElement') and request()==dict(rm='unchanged')
    checks['magic_target_labels_are_plain_text']=page.locator('#magicTargetChoices button').first.inner_text().startswith('<img src=x onerror=alert(1)>') and page.locator('#magicTargetChoices img').count()==0 and 'Worker A' in page.locator('#magicTargetActors').inner_text()
    page.locator('#magicTargetChoices button').first.tap()
    checks['magic_target_tap_captures_session_and_target_once']=request()==dict(rm='magictarget',value='session-A|target-1') and page.evaluate('magicRequests.length')==1
    page.locator('#magicTargetChoices button').first.focus()
    page.evaluate('window.savedMagicChoice=document.activeElement')
    model['magicTarget']['entries'][0]['label']='Updated target'
    model['magicTarget']['entries'].reverse()
    reset()
    render()
    checks['magic_target_live_reorder_preserves_exact_focused_target']=page.evaluate('savedMagicChoice===document.activeElement&&savedMagicChoice.dataset.value==="session-A|target-1"') and request()==dict(rm='unchanged')
    model['magicTarget']['entries']=model['magicTarget']['entries'][:1]
    render()
    checks['magic_target_removal_clears_old_choice_and_focuses_heading']=page.locator('#magicTargetChoices button').count()==1 and page.locator('#magicTargetTitle').evaluate('e=>e===document.activeElement') and page.evaluate('!savedMagicChoice.isConnected')
    model['magicTarget']['entries'][0]['reason']='No longer visible.'
    render()
    page.locator('#magicTargetChoices button').evaluate('e=>e.click()')
    checks['magic_target_stale_row_disabled_with_reason']=page.locator('#magicTargetChoices button').is_disabled() and 'No longer visible.' in page.locator('#magicTargetChoices button').inner_text() and request()==dict(rm='unchanged')
    model['magicTarget']['entries'][0]['reason']=''
    model['magicTarget']['reason']='Selection changed. Close and choose again.'
    render()
    page.locator('#magicTargetChoices button').evaluate('e=>e.click()')
    checks['magic_target_changed_actor_blocks_all_choices']=page.locator('#magicTargetChoices button').is_disabled() and page.locator('#magicTargetBlocked').is_visible() and request()==dict(rm='unchanged')
    page.keyboard.press('Escape')
    checks['magic_target_escape_closes_only_current_session']=not page.locator('#magicTargets').evaluate('e=>e.open') and request()==dict(rm='magictargetclose',value='session-A') and page.locator('#magicTargetOpener').evaluate('e=>e===document.activeElement')
    render()
    checks['magic_target_pending_snapshot_does_not_reopen_dismissed_session']=not page.locator('#magicTargets').evaluate('e=>e.open')
    model['magicTarget'].update(session='session-B',reason='')
    render()
    checks['magic_target_new_session_opens_with_same_unit_id']=page.locator('#magicTargets').evaluate('e=>e.open') and page.locator('#magicTargetChoices button').first.get_attribute('data-value')=='session-B|target-2'
    reset()
    page.locator('#magicTargets [data-ui=magictarget-close]').tap()
    checks['magic_target_close_uses_new_session_token']=request()==dict(rm='magictargetclose',value='session-B')
    model['magicTarget'].update(open=False)
    render()
    checks['magic_target_backend_close_clears_rows']=page.locator('#magicTargetChoices button').count()==0 and not page.locator('#magicTargets').evaluate('e=>e.open')
    model['magicTarget'].update(open=True,session='session-C',entries=[])
    reset()
    render()
    checks['magic_target_empty_view_explains_without_closing_or_command']=page.locator('#magicTargetEmpty').is_visible() and page.locator('#magicTargets').evaluate('e=>e.open') and request()==dict(rm='unchanged')
    model['magicTarget']['entries']=[dict(ref='target-'+str(i),label='Visible friendly or hostile unit '+str(i),race='Human',x=i,y=20,z=1,reason='') for i in range(40)]
    render()
    for width,height in ((320,568),(390,625),(768,844)):
        page.set_viewport_size(dict(width=width,height=height))
        fits=page.locator('#magicTargets [data-ui=magictarget-close]').evaluate('e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.top>=0&&r.bottom<=innerHeight}')
        fits &= page.locator('#magicTargetChoices button').evaluate_all('els=>els.every(e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth})')
        fits &= page.locator('#magicTargets .drawerbody').evaluate('e=>e.scrollHeight>e.clientHeight&&getComputedStyle(e).overflowY==="auto"')
        checks[f'magic_target_scroll_and_fixed_close_fit_{width}_{height}']=fits
    page.set_viewport_size(dict(width=390,height=625))
    page.screenshot(path=str(OUTPUT_DIR / 'magic-target-hud.png'))
    model['magicTarget'].update(open=False)
    model['tab']='orders'
    render()
    page.locator('#page-orders details').evaluate('e=>e.open=true')
    page.locator('#commands [data-value=magictarget]').focus()
    page.evaluate('window.savedMagicCommand=document.activeElement')
    other['reason']='This unit cannot use mental abilities.'
    render()
    checks['all_commands_live_eligibility_keeps_focused_identity']=page.evaluate('savedMagicCommand===document.activeElement&&savedMagicCommand.dataset.value==="magictarget"')
    reset()
    page.locator('#commands [data-value=magictarget]').tap()
    checks['magic_target_available_from_all_commands']=request()==dict(rm='action',value='magictarget')
    page.locator('#quickDock [data-ui=controls-open]').tap()
    model['magicTarget'].update(open=True,session='session-D')
    reset()
    render()
    checks['magic_target_replaces_local_controls_without_game_command']=page.locator('#magicTargets').evaluate('e=>e.open') and not page.locator('#borderControls').evaluate('e=>e.open') and request()==dict(rm='unchanged')
    page.close()


def check_control_groups(browser, html, source_model, result):
    model=copy.deepcopy(source_model)
    model.update(tab='units',selection=1)
    groups=dict(selection='selection-A',selectedCount=1,setReason='',addReason='',groups=[dict(number=i,count=2 if i==1 else 0,names=['Worker A','Worker B'] if i==1 else [],reason='' if i==1 else 'This group is empty.') for i in range(1,10)])
    model['controlGroups']=groups
    page=browser.new_page(viewport=dict(width=390,height=625),is_mobile=True,has_touch=True)
    page.on('pageerror',lambda error:result['errors'].append(str(error)))
    page.set_content(html,wait_until='domcontentloaded')
    checks=result['checks']

    def render(): page.evaluate('m=>updateHUD(m)',model)
    def reset(): page.evaluate("window.testLastURL='byond://?rm=unchanged'")
    def request(): return {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}

    render()
    reset()
    page.locator('#groupsOpener').tap()
    checks['groups_open_is_local_and_preserves_orders']=page.locator('#unitGroups').evaluate('e=>e.open') and request()==dict(rm='unchanged')
    checks['groups_display_nine_numbered_rows_and_original_members']=page.locator('#groupRows .unitgroup').count()==9 and page.locator('#groupRows .unitgroup').first.locator('.groupmembers').inner_text()=='Worker A, Worker B'
    page.locator('#groupRows .unitgroup').first.get_by_role('button',name='Recall group 1',exact=True).tap()
    checks['groups_recall_targets_current_group_without_selection_binding']=request()==dict(rm='controlgroup',value='1|Select|')
    reset()
    page.locator('#groupRows .unitgroup').nth(1).get_by_role('button',name='Recall group 2',exact=True).evaluate('e=>e.click()')
    checks['groups_empty_recall_disabled_with_reason']=page.locator('#groupRows .unitgroup').nth(1).get_by_role('button',name='Recall group 2',exact=True).is_disabled() and request()==dict(rm='unchanged')
    page.locator('#groupRows .unitgroup').nth(1).get_by_role('button',name='Set group 2 from selected units',exact=True).tap()
    checks['groups_set_binds_exact_group_and_selection_snapshot']=request()==dict(rm='controlgroup',value='2|Set|selection-A')
    page.locator('#groupRows .unitgroup').first.get_by_role('button',name='Add selected units to group 1',exact=True).tap()
    checks['groups_add_binds_exact_group_and_selection_snapshot']=request()==dict(rm='controlgroup',value='1|Add|selection-A')
    page.locator('#groupRows .unitgroup').first.get_by_role('button',name='Add selected units to group 1',exact=True).focus()
    page.evaluate('window.savedGroupWrite=document.activeElement')
    model['notice']='Work progressed'
    render()
    checks['groups_world_tick_keeps_focused_write_identity']=page.evaluate('savedGroupWrite===document.activeElement')
    groups['selection']='selection-B'
    groups['selectedCount']=2
    render()
    checks['groups_new_selection_replaces_old_write_instead_of_retargeting']=page.evaluate('!savedGroupWrite.isConnected') and page.locator('#groupRows h3').first.evaluate('e=>e===document.activeElement') and '2 selected' in page.locator('#groupsSelection').inner_text()
    page.locator('#groupRows .unitgroup').first.get_by_role('button',name='Add selected units to group 1',exact=True).tap()
    checks['groups_new_write_uses_new_selection_token']=request()==dict(rm='controlgroup',value='1|Add|selection-B')
    groups.update(selection='',selectedCount=0,setReason='Select your own living units.',addReason='Select your own living units.')
    render()
    reset()
    page.locator('#groupRows .unitgroup').first.locator('.groupwrite button').evaluate_all('els=>els.forEach(e=>e.click())')
    checks['groups_missing_selection_blocks_writes_but_keeps_recall']=page.locator('#groupRows .groupwrite button').evaluate_all('els=>els.every(e=>e.disabled)') and not page.locator('#groupRows .unitgroup').first.get_by_role('button',name='Recall group 1',exact=True).is_disabled() and page.locator('#groupsReason').inner_text()=='Select your own living units.' and request()==dict(rm='unchanged')
    groups['groups'][0]['names']=['<b>plain unit name</b>']
    groups['groups'][0]['count']=1
    render()
    checks['groups_member_names_are_plain_text']=page.locator('#groupRows .groupmembers').first.inner_text()=='<b>plain unit name</b>' and page.locator('#groupRows .groupmembers b').count()==0
    for width,height in ((320,568),(390,625),(768,844)):
        page.set_viewport_size(dict(width=width,height=height))
        fits=page.locator('#unitGroups [data-ui=groups-close]').evaluate('e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.top>=0&&r.bottom<=innerHeight}')
        fits &= page.locator('#groupRows button').evaluate_all('els=>els.every(e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth})')
        fits &= page.locator('#unitGroups .drawerbody').evaluate('e=>e.scrollHeight>e.clientHeight&&getComputedStyle(e).overflowY==="auto"')
        checks[f'groups_touch_controls_and_fixed_close_fit_{width}_{height}']=fits
    page.set_viewport_size(dict(width=390,height=625))
    page.screenshot(path=str(OUTPUT_DIR / 'control-groups-hud.png'))
    reset()
    page.keyboard.press('Escape')
    checks['groups_escape_closes_locally_without_deselecting']=not page.locator('#unitGroups').evaluate('e=>e.open') and page.locator('#groupsOpener').evaluate('e=>e===document.activeElement') and request()==dict(rm='unchanged')
    render()
    checks['groups_model_update_does_not_reopen_local_drawer']=not page.locator('#unitGroups').evaluate('e=>e.open')
    page.locator('#groupsOpener').tap()
    page.locator('#unitGroups [data-ui=groups-close]').tap()
    checks['groups_touch_close_stays_local']=not page.locator('#unitGroups').evaluate('e=>e.open') and request()==dict(rm='unchanged')
    page.locator('#groupsOpener').tap()
    model['magicTarget']=dict(open=True,session='magic-after-groups',reason='',actors=['Worker A'],entries=[])
    render()
    checks['magic_chooser_replaces_local_group_drawer']=not page.locator('#unitGroups').evaluate('e=>e.open') and page.locator('#magicTargets').evaluate('e=>e.open') and request()==dict(rm='unchanged')
    page.close()


def check_curated_controls(browser, html, source_model, result):
    """Existing non-border actions remain discoverable without changing routes."""
    ids = {'guard','rename','unitsay','emote','leader','mental','magictarget','clear',
           'jump','worldchat','clanchat','allyadd','allyremove','allylist','legends','music','help'}
    source = (ROOT/'game/Code/Remastered/Actions.dm').read_text()
    rows = re.findall(r'list\("([a-z]+)", "([^"]+)", (null|"[^"]*"), ([01]),', source)
    commands = [dict(id=key, label=label, key=shortcut.strip('"') if shortcut != 'null' else '', reason='')
                for key,label,shortcut,_ in rows if key in ids]
    checks = result['checks']
    checks['curated_drawer_uses_all17_existing_player_action_ids'] = {c['id'] for c in commands} == ids and len(commands)==17
    catalog = json.loads((ROOT/'game/Interface/border-controls.json').read_text())
    for width,height in ((320,568),(390,625),(768,844)):
        model = copy.deepcopy(source_model)
        model['commands'] = copy.deepcopy(commands)+[dict(id='admin_grant',label='Privileged command',reason='')]
        model['border'] = dict(visible=0,period='Day',controls=[dict(c,icon='',reason='',active=0) for c in catalog])
        page = browser.new_page(viewport=dict(width=width,height=height),is_mobile=True,has_touch=True)
        page.on('pageerror',lambda error:result['errors'].append(str(error)))
        page.set_content(html,wait_until='domcontentloaded')
        def render(): page.evaluate('m=>updateHUD(m)',model)
        def open_drawer():
            if not page.locator('#borderControls').evaluate('e=>e.open'):
                page.locator('#quickDock [data-ui=controls-open]').tap()
        def request(): return {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}
        render();open_drawer()
        checks[f'curated17_and_original44_have_distinct_routes_{width}'] = page.locator('#borderCatalog [data-do=borderaction]').count()==44 and set(page.locator('#borderCatalog [data-do=action]').evaluate_all('els=>els.map(e=>e.dataset.value)'))==ids and not page.locator('#borderCatalog [data-control=admin_grant]').count()
        page.evaluate("window.testLastURL='byond://?rm=unchanged'")
        search = page.locator('#controlSearch')
        search.fill('rename')
        checks[f'curated_search_finds_rename_without_executing_{width}'] = page.locator('#borderCatalog [data-control]:visible').evaluate_all('els=>els.map(e=>e.dataset.control)')==['rename'] and request()==dict(rm='unchanged')
        rename = next(c for c in model['commands'] if c['id']=='rename')
        rename['reason']='Select your own living units.';render()
        button = page.locator('#borderCatalog [data-control=rename] button')
        button.evaluate('e=>e.click()')
        checks[f'curated_action_disabled_reason_blocks_request_{width}'] = button.is_disabled() and 'Select your own living units.' in page.locator('#borderCatalog [data-control=rename] .reason').inner_text() and request()==dict(rm='unchanged')
        rename['reason']='';render();button.focus()
        page.evaluate("window.savedCuratedButton=document.querySelector('#borderCatalog [data-control=rename] button')")
        model['notice']='Other workers are gathering';render()
        checks[f'curated_action_retains_button_search_and_focus_{width}'] = page.evaluate('savedCuratedButton===document.activeElement&&savedCuratedButton===document.querySelector("#borderCatalog [data-control=rename] button")') and search.input_value()=='rename'
        page.locator('#clearControlSearch').tap()
        exact=True;closed=True;fit=True
        for command in commands:
            open_drawer()
            button=page.locator('#borderCatalog [data-do=action][data-value='+command['id']+']')
            button.scroll_into_view_if_needed()
            fit &= button.evaluate('e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth}')
            button.tap()
            exact &= request()==dict(rm='action',value=command['id'])
            closed &= not page.locator('#borderControls').evaluate('e=>e.open')
        checks[f'curated17_taps_keep_original_action_routes_{width}']=exact
        checks[f'curated_prompt_and_camera_commands_close_drawer_{width}']=closed
        checks[f'curated_text_only_rows_fit_touch_targets_{width}']=fit and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        open_drawer();search.fill('rename')
        rename['label']='<b>Rename & inspect</b>';render()
        checks[f'curated_labels_are_plain_text_{width}']=page.locator('#borderCatalog [data-control=rename] h4').inner_text()=='<b>Rename & inspect</b>' and page.locator('#borderCatalog [data-control=rename] h4 b').count()==0
        if width==390:
            rename['label']='Rename selected units';render()
            page.screenshot(path=str(OUTPUT_DIR / 'curated-controls-hud.png'))
        page.close()


def check_stock_filters(browser, html, source_model, result):
    """Explicit mining opt-in stays readable and keeps existing task controls."""
    for width,height in ((320,568),(390,625),(768,844)):
        model=copy.deepcopy(source_model)
        model.update(tab='work',selection=1)
        model['units'][0]['selected']=True
        stock=model['settlement']['stockpile']
        stock.update(set=True,filter='mixed',accepts='Wood + stone')
        page=browser.new_page(viewport=dict(width=width,height=height),is_mobile=True,has_touch=True)
        page.on('pageerror',lambda error:result['errors'].append(str(error)))
        page.set_content(html,wait_until='domcontentloaded')
        def render():page.evaluate('m=>updateHUD(m)',model)
        def request():return {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}
        def reset():page.evaluate("window.testLastURL='byond://?rm=unchanged'")
        render();checks=result['checks']
        controls=page.locator('#stockfilters button')
        checks[f'mining_filter_preserves_three_existing_choices_{width}']=controls.evaluate_all('els=>els.map(e=>e.dataset.value)')==['wood','stone','mixed','mining'] and page.locator('#stockfilters [aria-pressed=true]').get_attribute('data-value')=='mixed'
        fit=True
        for value in ('wood','stone','mixed','mining'):
            button=page.locator('#stockfilters [data-value='+value+']');button.scroll_into_view_if_needed()
            fit &= button.evaluate('e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth}')
            button.tap()
            checks[f'stock_filter_exact_{value}_request_{width}']=request()==dict(rm='stockfilter',value=value)
        checks[f'mining_filters_touch_sized_without_horizontal_overflow_{width}']=fit and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        button=page.locator('#stockfilters [data-value=mining]');button.focus();page.evaluate('window.savedFilter=document.activeElement')
        stock.update(filter='mining',accepts='Stone, ores, sand, uncut gems and bones');reset();render()
        checks[f'mining_server_ack_keeps_focus_and_explains_contents_{width}']=page.evaluate('savedFilter===document.activeElement') and page.locator('#stockfilters [aria-pressed=true]').get_attribute('data-value')=='mining' and 'uncut gems and bones' in page.locator('#stockAccepts').inner_text() and request()==dict(rm='unchanged')
        model['tab']='orders';render()
        checks[f'mining_delivery_explains_filter_and_preserved_cargo_{width}']='uncut gems and bones' in page.locator('#deliveryReason').inner_text() and 'food and seeds stay carried' in page.locator('#deliveryReason').inner_text() and page.locator('#dropHint').inner_text()==('Add a delivery stop after queued tasks' if model['queue'] else 'Replace tasks with a delivery stop')
        model['tab']='units';render()
        checks[f'mining_auto_unload_hint_updates_without_replacing_unit_{width}']='uncut gems and bones' in page.locator('#units .autohint').inner_text() and 'wood and stone only' not in page.locator('#units .autohint').inner_text()
        model['tab']='work';render()
        if width==390:
            page.locator('#stockfilters').scroll_into_view_if_needed();page.screenshot(path=str(OUTPUT_DIR / 'mining-stockpile-hud.png'))
        page.close()


def main(portraits_only=False, mental_only=False, compact_only=False, magic_only=False, groups_only=False, curated_only=False):
    html = (ROOT / 'game/Interface/remastered.html').read_text().replace('window.location.href=', 'window.testLastURL=')
    unit = dict(ref='[0x1]', name='Worker A', race='Dwarf', level=1, role='Miner', skill=4, selected=True, portrait='', hp=90, maxhp=100, fullness=80, maxfullness=100, energy=80, cold=0, weight=20, capacity=50, warnings=[], order='Chopping', queued=2, job='manual', x=20, y=20, z=1, items=[], tools='Uses tools', equipment='Can wear armour', paused=False, blocked='', autoUnload=False, active=dict(ref='[0x10]', kind='Chop', name='Oak', x=21, y=20, z=1, index=0), pending=[dict(ref='[0x11]', index=1, kind='Mine', name='Stone', x=23, y=20, z=1), dict(ref='[0x12]', index=2, kind='Move', name='Grass', x=24, y=20, z=1)])
    unit['defense'] = dict(mode='assist', state='Help nearby', responding=False, target='', radius=8)
    model = dict(tab='units', notice='Ready', units=[unit], selection=1, multi=False, queue=False, season='Summer', day='Day', date=1, x=20, y=20, z=1, maxx=40, maxy=40, maxz=1, idle=0, alert=0, targets=[], mode='', tutorialHidden=True, milestones={}, commands=[], settlement=dict(stockpile=dict(set=True, x=20, y=20, z=1, filter='mixed', accepts='wood and stone'), jobs=[dict(id='manual', label='Manual')], recipes=[], units=[], message='Stockpile ready'))
    model['controlGroups']=dict(selection='work-fixture-selection',selectedCount=1,setReason='',addReason='',groups=[])
    result = {'html_sha256': hashlib.sha256((ROOT / 'game/Interface/remastered.html').read_bytes()).hexdigest(), 'catalog_sha256': hashlib.sha256((ROOT / 'game/Interface/border-controls.json').read_bytes()).hexdigest(), 'checks': {}, 'errors': [], 'scope': 'Touch DOM rendering/request contracts; no game effects simulated.'}
    if portraits_only or mental_only or compact_only or magic_only or groups_only or curated_only:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
            (check_curated_controls if curated_only else check_portraits if portraits_only else check_mental_action if mental_only else check_magic_target if magic_only else check_control_groups if groups_only else check_compact_layout)(browser, html, model, result)
            browser.close()
        return finish_result(result, 'hud-curated-controls-checks.json' if curated_only else 'hud-portrait-checks.json' if portraits_only else 'hud-mental-action-checks.json' if mental_only else 'hud-magic-target-checks.json' if magic_only else 'hud-control-groups-checks.json' if groups_only else 'hud-compact-checks.json')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        page = browser.new_page(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True)
        page.on('pageerror', lambda error: result['errors'].append(str(error)))
        page.set_content(html, wait_until='domcontentloaded')
        page.evaluate('m => updateHUD(m)', model)

        def request():
            return {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}

        defense = page.locator('#units select[data-do=defensemode]')
        result['checks']['defense_defaults_to_help_nearby_with_three_modes'] = defense.input_value() == 'assist' and defense.locator('option').all_text_contents() == ['Help nearby', 'Defend self', 'No response']
        hint = page.locator('#units .defenseoptions .hint').inner_text()
        result['checks']['defense_explains_radius_level_walls_and_route'] = all(s in hint for s in ('8 tiles', 'every direction', 'same level', 'across walls', 'route'))
        defense.select_option('self')
        result['checks']['defense_change_captures_exact_unit_and_mode'] = request() == dict(rm='defensemode', value='[0x1]|self')
        unit['defense'].update(mode='self', state='Defend self')
        page.evaluate('m => updateHUD(m)', model)
        defense.focus()
        page.evaluate("window.testLastURL='byond://?rm=unchanged';window.defenseControl=document.querySelector('#units select[data-do=defensemode]')")
        page.keyboard.press('Escape')
        result['checks']['escape_in_defense_select_does_not_deselect'] = request() == dict(rm='unchanged')
        unit['defense'].update(state='Responding', responding=True, target='Orc raider')
        page.evaluate('m => updateHUD(m)', model)
        result['checks']['defense_response_keeps_prior_work_and_queue_visible'] = page.locator('#units .defensestate').inner_text() == 'Responding · Orc raider' and page.locator('#units .currenttask').inner_text() == 'Work to resume: Chop · Oak (21, 20)' and page.locator('#units [data-do=removeorder]').first.get_attribute('data-value') == '[0x1]|1|[0x11]'
        result['checks']['live_status_update_keeps_defense_select_and_focus'] = page.evaluate("window.defenseControl===document.querySelector('#units select[data-do=defensemode]') && document.activeElement===window.defenseControl")
        # Fresh page avoids stale sticky-layer pixels after responsive resizes.
        defense_preview = browser.new_page(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True)
        defense_preview.set_content(html, wait_until='domcontentloaded')
        defense_preview.evaluate('m => updateHUD(m)', model)
        defense_preview.evaluate('window.scrollBy(0,document.querySelector("#units .card").getBoundingClientRect().top-document.querySelector(".commandbar").getBoundingClientRect().height-8)')
        defense_preview.screenshot(path=str(OUTPUT_DIR / 'defense-hud.png'))
        defense_preview.close()
        unit['defense'].update(state='Returning', target='')
        page.evaluate('m => updateHUD(m)', model)
        result['checks']['returning_status_keeps_prior_work_visible'] = page.locator('#units .defensestate').inner_text() == 'Returning' and 'Work to resume: Chop' in page.locator('#units .currenttask').inner_text()
        defense.select_option('off')
        result['checks']['no_response_requests_only_defense_mode'] = request() == dict(rm='defensemode', value='[0x1]|off') and page.locator('#units .unitpick').get_attribute('aria-pressed') == 'true'
        unit['defense'].update(mode='assist', state='Help nearby', responding=False)
        page.evaluate('m => updateHUD(m)', model)
        result['checks']['finished_response_restores_current_work_label'] = page.locator('#units .currenttask').inner_text() == 'Current: Chop · Oak (21, 20)'
        page.get_by_role('button', name='Add tasks', exact=True).tap()
        result['checks']['touch_add_tasks_request'] = request() == dict(rm='queue', value='add')
        model['queue'] = True
        page.evaluate('m => updateHUD(m)', model)
        result['checks']['add_tasks_is_visibly_active'] = page.locator('#queue').get_attribute('aria-pressed') == 'true' and page.locator('#doNow').get_attribute('aria-pressed') == 'false'
        page.locator('#deselect').tap()
        result['checks']['deselect_requests_clear_and_explains_continued_work'] = request() == dict(rm='action', value='clear') and 'Deselect (1)' in page.locator('#deselect').inner_text() and 'Work continues' in page.locator('#deselect').inner_text()
        page.locator('#deselect').focus()
        page.keyboard.press('Escape')
        result['checks']['hud_escape_requests_deselect'] = request() == dict(rm='action', value='clear')
        model['mode'] = 'PlaceWoodenWall'
        page.evaluate('m => updateHUD(m)', model)
        page.keyboard.press('Escape')
        result['checks']['hud_escape_cancels_placement_first'] = request() == dict(rm='cancelmode')
        page.evaluate("window.testLastURL='byond://?rm=unchanged';const input=document.createElement('input');input.id='typing-test';document.body.append(input);input.focus()")
        page.keyboard.press('Escape')
        result['checks']['hud_escape_ignores_text_input'] = request() == dict(rm='unchanged')
        page.locator('#typing-test').evaluate('el => el.remove()')
        model['mode'] = ''
        page.evaluate('m => updateHUD(m)', model)
        page.locator('#units [data-do=removeorder]').first.tap()
        result['checks']['pending_remove_captures_unit_index_and_task'] = request() == dict(rm='removeorder', value='[0x1]|1|[0x11]')
        page.locator('#units [data-do=unitpause]').tap()
        result['checks']['pause_captures_unit'] = request() == dict(rm='unitpause', value='[0x1]')
        unit['paused'] = True
        unit['blocked'] = 'Needs Pickaxe'
        page.evaluate('m => updateHUD(m)', model)
        result['checks']['blocked_unit_exposes_resume_and_reason'] = page.locator('#units [data-do=unitresume]').count() == 1 and 'Needs Pickaxe' in page.locator('#units').inner_text()
        page.locator('#units [data-do=autounload]').tap()
        result['checks']['auto_unload_captures_unit'] = request() == dict(rm='autounload', value='[0x1]')
        model['tab'] = 'orders'
        page.evaluate('m => updateHUD(m)', model)
        page.locator('#orderunits select[data-do=defensemode]').select_option('self')
        result['checks']['orders_card_defense_targets_its_unit'] = request() == dict(rm='defensemode', value='[0x1]|self')
        page.locator('[data-do=dropoff]').tap()
        result['checks']['delivery_request_and_queue_label'] = request() == dict(rm='dropoff', selection=model['controlGroups']['selection']) and 'after queued tasks' in page.locator('#dropHint').inner_text()
        model['tab'] = 'work'
        page.evaluate('m => updateHUD(m)', model)
        page.locator('[data-do=stockfilter][data-value=stone]').tap()
        result['checks']['stockpile_filter_request'] = request() == dict(rm='stockfilter', value='stone')
        model['selection'] = 0
        model['queue'] = False
        unit['selected'] = False
        page.evaluate('m => updateHUD(m)', model)
        result['checks']['empty_selection_disables_add_tasks'] = page.locator('#queue').is_disabled() and page.locator('#orderunits .card').count() == 0
        for width in (320, 390, 768):
            page.set_viewport_size(dict(width=width, height=844))
            page.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)')
            result['checks'][f'no_horizontal_overflow_{width}'] = page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            result['checks'][f'deselect_stays_visible_and_touch_sized_{width}'] = page.locator('#deselect').evaluate('el => {const r=el.getBoundingClientRect();return r.y>=0&&r.bottom<=innerHeight&&r.width>=44&&r.height>=44}')
        (OUTPUT_DIR / 'easy-orders-hud.png').parent.mkdir(exist_ok=True)
        page.set_viewport_size(dict(width=390, height=844))
        model['tab'] = 'orders'
        model['selection'] = 1
        unit['selected'] = True
        page.evaluate('m => updateHUD(m)', model)
        page.locator('#orderunits').scroll_into_view_if_needed()
        for width in (320, 390, 768):
            page.set_viewport_size(dict(width=width, height=844))
            result['checks'][f'defense_control_fits_and_is_touch_sized_{width}'] = page.locator('#orderunits select[data-do=defensemode]').evaluate('el=>{const r=el.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth&&document.documentElement.scrollWidth<=innerWidth}')
        page.set_viewport_size(dict(width=390, height=844))
        page.screenshot(path=str(OUTPUT_DIR / 'easy-orders-hud.png'))
        check_stock_filters(browser, html, model, result)
        check_live_unit_controls(browser, html, model, result)
        check_command_controls(page, browser, html, model, result)
        check_original_palette(browser, html, model, result)
        check_portraits(browser, html, model, result)
        check_mental_action(browser, html, model, result)
        check_compact_layout(browser, html, model, result)
        check_magic_target(browser, html, model, result)
        check_control_groups(browser, html, model, result)
        check_curated_controls(browser, html, model, result)
        browser.close()
    return finish_result(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, help='Fresh directory for reports/screenshots; keeps earlier evidence intact.')
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--portraits-only', action='store_true', help='Run only the focused resource-loading and portrait fallback checks.')
    group.add_argument('--mental-only', action='store_true', help='Run only the original mental-abilities action controls.')
    group.add_argument('--compact-only', action='store_true', help='Check initial unit visibility and control access on short screens.')
    group.add_argument('--magic-only', action='store_true', help='Check magic-target chooser request identity, live updates and touch layout.')
    group.add_argument('--groups-only', action='store_true', help='Check numbered control group touch routes and captured selection contracts.')
    group.add_argument('--curated-only', action='store_true', help='Check discoverability and routes for existing non-border actions.')
    args=parser.parse_args()
    if args.output_dir:
        OUTPUT_DIR=args.output_dir.resolve()
        if OUTPUT_DIR.exists():parser.error('Choose a fresh --output-dir to preserve earlier evidence')
        OUTPUT_DIR.mkdir(parents=True)
    raise SystemExit(main(args.portraits_only,args.mental_only,args.compact_only,args.magic_only,args.groups_only,args.curated_only))
