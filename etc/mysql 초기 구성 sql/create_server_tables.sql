CREATE DATABASE m_m;

use m_m;

CREATE table users(
	`id` varchar(200) NOT NULL,
	`pw` varchar(200) NOT NULL,
	`name` varchar(200) NOT NULL,
	`q_a` text,
	`servers` text,
	`join_date` DATETIME NOT NULL,
	PRIMARY KEY(id)
);

CREATE table servers(
	`id` int(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`name` varchar(200) NOT NULL,
	`ip` varchar(200) NOT NULL,
	`ssh_id` varchar(200) NOT NULL,
	`ssh_pw` varchar(200) NOT NULL,
	`port` int(11) NOT NULL,
	`OS` text,
	`kernel` text,
	`arch` text,
	`processor` text,
	`ram` text,
	`storage` text,
	`mysql_ver` text,
	`mysql_port` text,
	`mysql_reset_pw` text,
	`mysql_pw_policy_chk_name` varchar(20) DEFAULT 'OFF',
	`mysql_pw_policy_dic_file` varchar(20),
	`mysql_pw_policy_length` varchar(20) DEFAULT '8',
	`mysql_pw_policy_mix_count` varchar(20) DEFAULT '1',
	`mysql_pw_policy_num_count` varchar(20) DEFAULT '1',
	`mysql_pw_policy_type` varchar(20) DEFAULT 'MEDIUM',
	`mysql_pw_policy_special_count` varchar(20) DEFAULT '1',
	`users` text,
	`date` DATETIME NOT NULL
);

CREATE table server_check(
	`date` varchar(200) NOT NULL,
	`id` int(11) NOT NULL,
	`good` varchar(200) NOT NULL,
	`warning` varchar(200) NOT NULL,
	`danger` varchar(200) NOT NULL,
	`log` text NOT NULL,
	PRIMARY KEY(date, id)
);