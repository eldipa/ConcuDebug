define(['jquery', 'layout', 'underscore'], function ($, layout, _) {
    var CodeSelector = function (thread_follower) {
        this.thread_follower = thread_follower;

        var self = this;
        this._$file_selector = $('<input></input>')
            .addClass( "ui-widget ui-widget-content ui-state-default ui-corner-all" )
            .autocomplete({
                source: function search_for_suggestions(request, callback) {
                    var search_for_all = !request.term;

                    var safe_value = $.ui.autocomplete.escapeRegex(request.term);
                    var matcher = new RegExp(safe_value, 'i');

                    var thread_follower = self.thread_follower;

                    if (thread_follower.are_you_following_a_thread_group()) {
                        var thread_group_followed = thread_follower.thread_group_followed;
                        thread_group_followed.update_source_fullnames(function on_source_fullnames(files, msg) {
                            var all_options = _.map(files, function (obj) {
                                return {
                                    label: obj.file,
                                    value: obj.fullname
                                };
                            });

                            if (search_for_all) {
                                var options = all_options;
                            }
                            else {
                                var options = _.filter(all_options, function (opt) {
                                    return matcher.test(opt.label);
                                });
                            }

                            callback(options);
                        });
                    }
                    else {
                        callback([]);
                    }
                },

                select: function on_suggestion_selected(ev, ui) {
                    var file = ui.item.label;
                    var fullname = ui.item.value;

                    ui.item.value = ui.item.label;

                    thread_follower.update_button_bar_and_code_editor_to_show(fullname, 1, "0x00000000");
                }
        });

        this._$out_of_dom = this._$file_selector;
    };
    
    CodeSelector.prototype.__proto__ = layout.Panel.prototype;

    CodeSelector.prototype.render = function () {
        if (this._$out_of_dom) {
            this._$out_of_dom.appendTo(this.box);
            this._$out_of_dom = null;
        }
    };

    CodeSelector.prototype.unlink = function () {
        if (!this._$out_of_dom) {
            this._$out_of_dom = this._$file_selector.detach();
        }
    };

    CodeSelector.prototype.position = function (conf) {
        this._$file_selector.position(conf);
    };

    return {CodeSelector: CodeSelector};
});

