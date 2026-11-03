// OpenDream's client only knows which verbs it can run (the skin's macros: Restart, Quick,
// Attack...) for the entities its map renderer saw on the last frame
// (DreamViewOverlay.EntitiesInView, read by ClientVerbSystem). A headless client never draws,
// so that set stays empty and every macro would be ignored. This fills it the way the
// renderer does: everything around the player's mob, twice a second.
using System;
using System.Collections.Generic;
using System.Numerics;
using System.Reflection;
using Robust.Client.Graphics;
using Robust.Client.Player;
using Robust.Shared.GameObjects;
using Robust.Shared.IoC;
using Robust.Shared.Maths;
using Robust.Shared.Reflection;

namespace Robust.Client.WebView;

internal static class RelayView {
    private static Type? _overlayType;
    private static FieldInfo? _field;
    private static DateTime _next;
    private static bool _warned;

    public static void Refresh() {
        if (DateTime.UtcNow < _next) return;
        _next = DateTime.UtcNow.AddMilliseconds(500);
        try {
            _overlayType ??= IoCManager.Resolve<IReflectionManager>().GetType("OpenDreamClient.Rendering.DreamViewOverlay");
            if (_overlayType == null) return;
            var overlays = IoCManager.Resolve<IOverlayManager>();
            if (!overlays.HasOverlay(_overlayType)) return;
            var overlay = overlays.GetOverlay(_overlayType);
            _field ??= _overlayType.GetField("EntitiesInView");
            if (_field?.GetValue(overlay) is not HashSet<EntityUid> inView) return;
            var local = IoCManager.Resolve<IPlayerManager>().LocalEntity;
            if (local == null) return;
            var entities = IoCManager.Resolve<IEntityManager>();
            if (!entities.TryGetComponent(local.Value, out TransformComponent? transform)) return;
            var position = entities.System<SharedTransformSystem>().GetWorldPosition(transform);
            // About what a 33x19-tile view shows, plus a margin, like the renderer's scaled view box.
            var box = new Box2(position - new Vector2(22, 14), position + new Vector2(22, 14));
            inView.Clear();
            entities.System<EntityLookupSystem>().GetEntitiesIntersecting(transform.MapID, box, inView, LookupFlags.Approximate | LookupFlags.Uncontained);
            inView.Add(local.Value);
        } catch (Exception error) {
            if (_warned) return;
            _warned = true;
            RelayWebViewManager.Log($"view refresh failed: {error.Message}");
        }
    }
}
