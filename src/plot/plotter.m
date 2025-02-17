%% Plotter.m
%
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%
%   [+] Fecha: 14 Feb 2025
clc
close all
clear varibles

%% Main

% Pintamos las graficas correspondientes al balance global de potencias, el
% valor absoluto del flujo de potencia, perdias por enlaces - switches,
% perdidas por superar el valor máximo de la configuración de un enlace 
plotDeltaLoads_1(0,"../results/ieee123/")

% Pintamos el valor medio de todos los intantes de carga 
plotRangeLoads_1(0, 95, "../results/ieee123/")


% Pintamos las curvas de los balances
plotTemporalBalance(0, 95, "../results/ieee123/")