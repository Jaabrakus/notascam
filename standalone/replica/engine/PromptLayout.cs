using System;
using System.Numerics;
using Robust.Client.UserInterface;
using Robust.Client.UserInterface.Controls;
using Robust.Shared.Maths;

// Called once by OpenDream PromptWindow.Shown, before InputWindow grabs focus.
// It never changes list items, selection, labels, or response callbacks.
public static class PromptLayout {
    public static void Shown(OSWindow prompt) {
        var window=prompt.ClydeWindow;
        if(window==null)return;
        var scale=prompt.UIScale;
        var viewport=prompt.Owner?.Size.X / scale ?? 500;
        var bound=Math.Max(100,viewport-20);
        RefreshMeasurements(prompt);
        var list=FindList(prompt);
        if(list!=null && list.Parent is not ScrollContainer) {
            // A temporary Label measures the current font after attachment to
            // the scaled root. Nothing is rendered before it is removed.
            var label=new Label();
            list.AddChild(label);
            float width=0;
            for(int i=0;i<list.Count;i++) {
                label.Text=list[i].Text;
                label.Measure(new Vector2(float.PositiveInfinity,float.PositiveInfinity));
                width=Math.Max(width,label.DesiredSize.X);
            }
            list.RemoveChild(label);
            // Original row inset and vertical scrollbar need space as well.
            width+=40;
            var parent=list.Parent!;
            var scroll=new ScrollContainer {
                HScrollEnabled=true,VScrollEnabled=false,ReturnMeasure=true,
                MinWidth=Math.Min(width,Math.Min(480,bound-10)),
                MaxWidth=Math.Min(480,bound-10)
            };
            parent.RemoveChild(list);
            list.MinWidth=width;
            scroll.AddChild(list);
            parent.AddChild(scroll);
        }
        prompt.MinWidth=Math.Min(prompt.MinWidth,bound);
        prompt.MaxWidth=bound;
        prompt.InvalidateMeasure();
        prompt.Measure(new Vector2(bound,float.PositiveInfinity));
        var desired=new Vector2i((int)Math.Ceiling(prompt.DesiredSize.X*scale),(int)Math.Ceiling(prompt.DesiredSize.Y*scale));
        if(window.Size!=desired)window.Size=desired;
        prompt.CenterInitialPromptOnOwner();
    }
    private static void RefreshMeasurements(Control control) {
        // Label caches pixel glyph widths; invalidate with its own public
        // font setter while retaining the exact existing font override.
        if(control is Label label)label.FontOverride=label.FontOverride;
        for(int i=0;i<control.ChildCount;i++)RefreshMeasurements(control.GetChild(i));
        control.InvalidateMeasure();
    }
    private static ItemList? FindList(Control control) {
        if(control is ItemList list)return list;
        for(int i=0;i<control.ChildCount;i++) {
            var found=FindList(control.GetChild(i));
            if(found!=null)return found;
        }
        return null;
    }
}
