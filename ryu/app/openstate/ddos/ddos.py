import logging
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls

LOG = logging.getLogger('app.openstate.ddos')

class OSDDoS(app_manager.RyuApp):

	def __init__(self, *args, **kwargs):
		super(OSDDoS, self).__init__(*args, **kwargs)

	def add_flow(self, datapath, table_id, priority, match, actions):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		if len(actions) > 0:
			inst = [parser.OFPInstructionActions(
					ofproto.OFPIT_APPLY_ACTIONS, actions)]
		else:
			inst = []
		mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id,
								priority=priority, match=match, instructions=inst)
		datapath.send_msg(mod)

	@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
	def switch_features_handler(self, event):

		""" Switche sent his features, check if OpenState supported """
		msg = event.msg
		datapath = msg.datapath
		ofp = datapath.ofproto
		parser = datapath.ofproto_parser

		LOG.info("Configuring switch %d..." % datapath.id)

		
		
		for table in range(0,2):
			""" Set tables as stateful """
			req = parser.OFPExpMsgConfigureStatefulTable(datapath=datapath, 
					table_id=table, 
					stateful=1)
			datapath.send_msg(req)

			""" Set lookup extractor = {ip_src, ip_dst, tcp_src, tcp_dst} """
			req = parser.OFPExpMsgKeyExtract(datapath=datapath, 									
					command=ofp.OFPSC_EXP_SET_L_EXTRACTOR, 
					fields=[ofp.OXM_OF_IPV4_SRC,ofp.OXM_OF_IPV4_DST,ofp.OXM_OF_TCP_SRC,ofp.OXM_OF_TCP_DST], 
					table_id=table)
			datapath.send_msg(req)

			""" Set update extractor = {ip_src, ip_dst, tcp_src, tcp_dst} (same as lookup) """
			req = parser.OFPExpMsgKeyExtract(datapath=datapath, 
					command=ofp.OFPSC_EXP_SET_U_EXTRACTOR, 
					fields=[ofp.OXM_OF_IPV4_SRC,ofp.OXM_OF_IPV4_DST,ofp.OXM_OF_TCP_SRC,ofp.OXM_OF_TCP_DST],
					table_id=table)
			datapath.send_msg(req)


		""" Configure meter 1 """
		b1 = parser.OFPMeterBandDscpRemark(rate=10, prec_level=1)
		req = parser.OFPMeterMod(datapath, command=ofp.OFPMC_ADD, flags=ofp.OFPMF_PKTPS, meter_id=1, bands=[b1])
		datapath.send_msg(req)

		""" Table 0 """
		match = parser.OFPMatch(eth_type=0x0800,ipv4_dst="10.0.0.2",state=0)
		actions = [parser.OFPExpActionSetState(state=1, table_id=0, idle_timeout=30)]
		inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions), parser.OFPInstructionMeter(meter_id=1),
				parser.OFPInstructionGotoTable(table_id=1)]
		mod = parser.OFPFlowMod(datapath=datapath, table_id=0,
								priority=10, match=match, instructions=inst)
		datapath.send_msg(mod)

		match = parser.OFPMatch(eth_type=0x0800,ipv4_dst="10.0.0.2",state=1)
		inst = [parser.OFPInstructionGotoTable(table_id=1)]
		mod = parser.OFPFlowMod(datapath=datapath, table_id=0,
								priority=10, match=match, instructions=inst)
		datapath.send_msg(mod)

		match = parser.OFPMatch(eth_type=0x0800,ipv4_dst="10.0.0.1")
		actions = [parser.OFPActionOutput(1)]
		inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
		mod = parser.OFPFlowMod(datapath=datapath, table_id=0,
								priority=10, match=match, instructions=inst)
		datapath.send_msg(mod)

		""" Table 1 """
		match = parser.OFPMatch(state=0,eth_type=0x0800,ipv4_dst="10.0.0.2",ip_dscp=10)
		actions = [parser.OFPActionOutput(2)]
		inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
		mod = parser.OFPFlowMod(datapath=datapath, table_id=1,
								priority=10, match=match, instructions=inst)
		datapath.send_msg(mod)

		match = parser.OFPMatch(eth_type=0x0800,ipv4_dst="10.0.0.2",ip_dscp=12)
		actions = [parser.OFPExpActionSetState(state=1, table_id=1, idle_timeout=30)]
		inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
		mod = parser.OFPFlowMod(datapath=datapath, table_id=1,
								priority=10, match=match, instructions=inst)
		datapath.send_msg(mod)

		match = parser.OFPMatch(state=1,eth_type=0x0800,ipv4_dst="10.0.0.2", ip_dscp=10)
		actions = []
		inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
		mod = parser.OFPFlowMod(datapath=datapath, table_id=1,
								priority=10, match=match, instructions=inst)
		datapath.send_msg(mod)
