/**
 *  Copyright (C) 2010 Cloud.com, Inc.  All rights reserved.
 * 
 * This software is licensed under the GNU General Public License v3 or later.
 * 
 * It is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or any later version.
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 * 
 */
package com.cloud.host.dao;

import java.util.Date;
import java.util.List;

import com.cloud.host.Host;
import com.cloud.host.HostVO;
import com.cloud.host.Status;
import com.cloud.host.Host.Type;
import com.cloud.host.Status.Event;
import com.cloud.info.RunningHostCountInfo;
import com.cloud.utils.db.GenericDao;

/**
 * Data Access Object for server
 * 
 */
public interface HostDao extends GenericDao<HostVO, Long> {
    List<HostVO> listBy(Host.Type type, Long clusterId, Long podId, long dcId);
    
    long countBy(long clusterId,  Status... statuses);
 
    List<HostVO> listByDataCenter(long dcId);
	List<HostVO> listByHostPod(long podId);
	List<HostVO> listByStatus(Status... status);
	List<HostVO> listBy(Host.Type type, long dcId);
	HostVO findSecondaryStorageHost(long dcId);
	List<HostVO> listByCluster(long clusterId);
	/**
	 * Lists all secondary storage hosts, across all zones
	 * @return list of Hosts
	 */
	List<HostVO> listSecondaryStorageHosts();
	
	/**
	 * Mark all hosts in Up or Orphaned state as disconnected.  This method
	 * is used at AgentManager startup to reset all of the connections.
	 * 
	 * @param msId management server id.
     * @param statuses states of the host.
	 */
	void markHostsAsDisconnected(long msId, Status... states);
	
	List<HostVO> findLostHosts(long timeout);
	
	List<HostVO> findHostsLike(String hostName);

	/**
	 * Find hosts that are directly connected.
	 */
	List<HostVO> findDirectlyConnectedHosts();
	
    List<HostVO> findDirectAgentToLoad(long msid, long lastPingSecondsAfter, Long limit);
	

	/**
	 * Mark the host as disconnected if it is in one of these states.
	 * The management server id is set to null.
	 * The lastPinged timestamp is set to current.
	 * The state is set to the state passed in.
	 * The disconnectedOn timestamp is set to current.
	 * 
	 * @param host host to be marked
	 * @param state state to be set to.
	 * @param ifStates only if it is one of these states.
	 * @return true if it's updated; false if not.
	 */
	boolean disconnect(HostVO host, Event event, long msId);
	
	boolean connect(HostVO host, long msId);
	
	HostVO findByStorageIpAddressInDataCenter(long dcId, String privateIpAddress);
    HostVO findByPrivateIpAddressInDataCenter(long dcId, String privateIpAddress);

	/**
	 * find a host by its mac address
	 * @param macAddress
	 * @return HostVO or null if not found.
	 */
	public HostVO findByGuid(String macAddress);
	

	/**
	 * find all hosts of a certain type in a data center
	 * @param type
	 * @param routingCapable
	 * @param dcId
	 * @return
	 */
	List<HostVO> listByTypeDataCenter(Host.Type type, long dcId);

	/**
	 * find all hosts of a particular type
	 * @param type
	 * @return
	 */
	List<HostVO> listByType(Type type, boolean routingCapable);

	/**
	 * Find hosts that have not responded to a ping regardless of state
	 * @param timeout
	 * @param type
	 * @return
	 */
	List<HostVO> findLostHosts2(long timeout, Type type);
	
	/**
	 * update the host and changes the status depending on the Event and
	 * the current status.  If the status changed between
	 * @param host host object to change
	 * @param event event that happened.
	 * @param management server who's making this update
	 * @return true if updated; false if not.
	 */
	boolean updateStatus(HostVO host, Event event, long msId);
	
    List<RunningHostCountInfo> getRunningHostCounts(Date cutTime);
    
    long getNextSequence(long hostId);
    
    void loadDetails(HostVO host);

    void loadHostTags(HostVO host);
}
